#if UNITY_EDITOR || QUESTLINE_DEV
using System;
using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Questline.Companion
{
    /// <summary>
    /// Thin TCP + NDJSON listener (ADR-0005 QuestlineWire). Dev/Editor only.
    /// Games call <see cref="EnsureStarted"/> from bootstrap under the same define gate
    /// as hook registration. Mutually exclusive with AltTester Prefab on the same port.
    /// </summary>
    public sealed class QuestlineWireServer : MonoBehaviour
    {
        public const int ProtocolVersion = 2;
        public const int DefaultPort = 13000;
        public const string CompanionVersion = "0.1.0";

        private static QuestlineWireServer _instance;

        private TcpListener _listener;
        private Thread _acceptThread;
        private volatile bool _running;
        private int _port = DefaultPort;
        private readonly ConcurrentQueue<Action> _mainThreadQueue = new ConcurrentQueue<Action>();

        /// <summary>Start (or no-op if already running) the Wire listener on loopback.</summary>
        public static QuestlineWireServer EnsureStarted(int port = DefaultPort)
        {
            if (_instance != null)
            {
                if (!_instance._running)
                    _instance.StartListener(port);
                return _instance;
            }

            var go = new GameObject("QuestlineWireServer");
            DontDestroyOnLoad(go);
            _instance = go.AddComponent<QuestlineWireServer>();
            _instance.StartListener(port);
            return _instance;
        }

        /// <summary>Stop listener and destroy the host (tests / teardown).</summary>
        public static void StopAndDestroy()
        {
            if (_instance == null) return;
            _instance.StopListener();
            Destroy(_instance.gameObject);
            _instance = null;
        }

        public static bool IsRunning => _instance != null && _instance._running;

        public static int BoundPort => _instance != null ? _instance._port : -1;

        private void Update()
        {
            while (_mainThreadQueue.TryDequeue(out var action))
            {
                try
                {
                    action();
                }
                catch (Exception ex)
                {
                    Debug.LogException(ex);
                }
            }
        }

        private void OnDestroy()
        {
            StopListener();
            if (_instance == this)
                _instance = null;
        }

        private void StartListener(int port)
        {
            if (_running) return;
            _port = port > 0 ? port : DefaultPort;
            try
            {
                _listener = new TcpListener(IPAddress.Loopback, _port);
                _listener.Start();
            }
            catch (Exception ex)
            {
                Debug.LogError(
                    $"[QuestlineWire] failed to bind 127.0.0.1:{_port}: {ex.Message}. " +
                    "Another listener (e.g. AltTester Prefab) may own the port.");
                throw;
            }

            _running = true;
            _acceptThread = new Thread(AcceptLoop)
            {
                IsBackground = true,
                Name = "QuestlineWireAccept",
            };
            _acceptThread.Start();
            Debug.Log($"[QuestlineWire] listening on 127.0.0.1:{_port} (v{ProtocolVersion})");

            // PerfProbe companion counters (phase-09 / QL-3) — no-op if already registered.
            try
            {
                QuestlinePerfProvider.EnsureRegistered();
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[QuestlineWire] PerfProvider register failed: {ex.Message}");
            }
        }

        private void StopListener()
        {
            _running = false;
            try
            {
                _listener?.Stop();
            }
            catch
            {
                // ignore
            }
            _listener = null;
            if (_acceptThread != null && _acceptThread.IsAlive)
            {
                try
                {
                    _acceptThread.Join(500);
                }
                catch
                {
                    // ignore
                }
            }
            _acceptThread = null;
        }

        private void AcceptLoop()
        {
            while (_running)
            {
                TcpClient client = null;
                try
                {
                    client = _listener.AcceptTcpClient();
                }
                catch (SocketException)
                {
                    if (!_running) break;
                    continue;
                }
                catch (ObjectDisposedException)
                {
                    break;
                }

                if (client == null) continue;
                var thread = new Thread(() => HandleClient(client))
                {
                    IsBackground = true,
                    Name = "QuestlineWireClient",
                };
                thread.Start();
            }
        }

        private void HandleClient(TcpClient client)
        {
            using (client)
            using (var stream = client.GetStream())
            {
                var buffer = new byte[8192];
                var pending = new StringBuilder();
                while (_running && client.Connected)
                {
                    int read;
                    try
                    {
                        read = stream.Read(buffer, 0, buffer.Length);
                    }
                    catch
                    {
                        break;
                    }
                    if (read <= 0) break;

                    pending.Append(Encoding.UTF8.GetString(buffer, 0, read));
                    while (true)
                    {
                        var text = pending.ToString();
                        var nl = text.IndexOf('\n');
                        if (nl < 0) break;
                        var line = text.Substring(0, nl).Trim();
                        pending.Remove(0, nl + 1);
                        if (line.Length == 0) continue;
                        var response = DispatchLine(line);
                        var payload = Encoding.UTF8.GetBytes(response + "\n");
                        try
                        {
                            stream.Write(payload, 0, payload.Length);
                            stream.Flush();
                        }
                        catch
                        {
                            return;
                        }
                    }
                }
            }
        }

        private string DispatchLine(string line)
        {
            string id = "0";
            try
            {
                if (!WireJson.TryParseRequest(line, out id, out var op, out var paramsJson))
                {
                    return WireJson.ErrorResponse(id, "authoring", "malformed request JSON");
                }

                if (string.IsNullOrEmpty(op))
                    return WireJson.ErrorResponse(id, "authoring", "missing op");

                switch (op)
                {
                    case "hello":
                        return RunOnMainThread(() => WireJson.OkResponse(id, HelloResult()));
                    case "ping":
                        return WireJson.OkResponse(id, "{\"pong\":true}");
                    case "app_state":
                        return RunOnMainThread(() => WireJson.OkResponse(id, AppStateResult()));
                    case "hooks_manifest":
                        return RunOnMainThread(() =>
                        {
                            var raw = QuestlineHooks.GetManifestJson();
                            // GetManifestJson already returns {"hooks":[...]} — wrap as result object.
                            return WireJson.OkResponse(id, raw);
                        });
                    case "call_hook":
                        return RunOnMainThread(() => InvokeHookOp(id, paramsJson));
                    case "hierarchy":
                        return RunOnMainThread(() =>
                            WireJson.OkResponse(id, QuestlineWireUi.HierarchyResult(paramsJson)));
                    case "find":
                        return RunOnMainThread(() =>
                            WireJson.OkResponse(id, QuestlineWireUi.FindResult(paramsJson, all: false)));
                    case "find_all":
                        return RunOnMainThread(() =>
                            WireJson.OkResponse(id, QuestlineWireUi.FindResult(paramsJson, all: true)));
                    case "tap":
                        return RunOnMainThread(() =>
                            WireJson.OkResponse(id, QuestlineWireUi.TapResult(paramsJson)));
                    case "screenshot":
                        return RunOnMainThread(() =>
                            WireJson.OkResponse(id, QuestlineWireUi.ScreenshotResult()));
                    default:
                        return WireJson.ErrorResponse(id, "authoring", $"unknown op: {op}");
                }
            }
            catch (QuestlineWireUi.ElementNotFoundException ex)
            {
                return WireJson.ErrorResponse(id, "element_not_found", ex.Message);
            }
            catch (Exception ex)
            {
                Debug.LogException(ex);
                var code = ClassifyException(ex);
                return WireJson.ErrorResponse(id, code, ex.Message);
            }
        }

        private string InvokeHookOp(string id, string paramsJson)
        {
            if (!WireJson.TryGetString(paramsJson, "name", out var name) || string.IsNullOrEmpty(name))
                return WireJson.ErrorResponse(id, "authoring", "call_hook requires params.name");

            var argsJson = "[]";
            if (WireJson.TryGetRawArray(paramsJson, "args", out var arr))
                argsJson = arr;

            try
            {
                var result = QuestlineHooks.InvokeHook(name, argsJson);
                // Encode as JSON value inside result.result
                var encoded = string.IsNullOrEmpty(result) ? "null" : result;
                return WireJson.OkResponse(id, "{\"value\":" + encoded + "}");
            }
            catch (ArgumentException ex)
            {
                return WireJson.ErrorResponse(id, "authoring", ex.Message);
            }
            catch (InvalidOperationException ex)
            {
                // unknown hook
                return WireJson.ErrorResponse(id, "authoring", ex.Message);
            }
            catch (Exception ex)
            {
                return WireJson.ErrorResponse(id, "test", ex.Message);
            }
        }

        private static string HelloResult()
        {
            var scene = SceneManager.GetActiveScene().name ?? "";
            var sb = new StringBuilder();
            sb.Append('{');
            sb.Append("\"protocol_version\":").Append(ProtocolVersion).Append(',');
            sb.Append("\"companion_version\":\"").Append(WireJson.Escape(CompanionVersion)).Append("\",");
            sb.Append("\"scene\":\"").Append(WireJson.Escape(scene)).Append("\",");
            sb.Append("\"features\":[\"hooks\",\"ui\"]");
            sb.Append('}');
            return sb.ToString();
        }

        private static string AppStateResult()
        {
            var scene = SceneManager.GetActiveScene().name ?? "";
            var paused = Mathf.Approximately(Time.timeScale, 0f);
            var sb = new StringBuilder();
            sb.Append('{');
            sb.Append("\"foreground\":true,");
            sb.Append("\"scene\":\"").Append(WireJson.Escape(scene)).Append("\",");
            sb.Append("\"paused\":").Append(paused ? "true" : "false");
            sb.Append('}');
            return sb.ToString();
        }

        private static string ClassifyException(Exception ex)
        {
            if (ex is QuestlineWireUi.ElementNotFoundException)
                return "element_not_found";
            if (ex is ArgumentException || ex is FormatException)
                return "authoring";
            if (ex is InvalidOperationException)
                return "authoring";
            return "test";
        }

        private string RunOnMainThread(Func<string> work)
        {
            // Client threads must never touch Unity APIs directly — always queue to Update().
            string result = null;
            Exception error = null;
            using (var done = new ManualResetEventSlim(false))
            {
                _mainThreadQueue.Enqueue(() =>
                {
                    try
                    {
                        result = work();
                    }
                    catch (Exception ex)
                    {
                        error = ex;
                    }
                    finally
                    {
                        done.Set();
                    }
                });

                if (!done.Wait(30000))
                    return WireJson.ErrorResponse("0", "infra", "main-thread dispatch timed out");
            }

            if (error != null)
                throw error;
            return result ?? WireJson.ErrorResponse("0", "infra", "empty main-thread result");
        }
    }

    /// <summary>Minimal JSON helpers for Wire NDJSON (no third-party deps).</summary>
    internal static class WireJson
    {
        public static string Escape(string value)
        {
            if (string.IsNullOrEmpty(value)) return "";
            return value.Replace("\\", "\\\\").Replace("\"", "\\\"");
        }

        public static string OkResponse(string id, string resultJsonObject)
        {
            var sb = new StringBuilder();
            sb.Append("{\"v\":1,\"id\":\"").Append(Escape(id)).Append("\",\"ok\":true,\"result\":");
            sb.Append(resultJsonObject);
            sb.Append('}');
            return sb.ToString();
        }

        public static string ErrorResponse(string id, string code, string message)
        {
            var sb = new StringBuilder();
            sb.Append("{\"v\":1,\"id\":\"").Append(Escape(id ?? "0")).Append("\",\"ok\":false,\"error\":{");
            sb.Append("\"code\":\"").Append(Escape(code)).Append("\",");
            sb.Append("\"message\":\"").Append(Escape(message ?? "")).Append('"');
            sb.Append("}}");
            return sb.ToString();
        }

        public static bool TryParseRequest(string line, out string id, out string op, out string paramsJson)
        {
            id = "0";
            op = null;
            paramsJson = "{}";
            if (string.IsNullOrWhiteSpace(line)) return false;
            var text = line.Trim();
            if (text[0] != '{') return false;

            if (!TryGetString(text, "id", out id))
                id = "0";
            if (!TryGetString(text, "op", out op))
                return false;

            if (TryGetRawObject(text, "params", out var p))
                paramsJson = p;
            else
                paramsJson = "{}";
            return true;
        }

        public static bool TryGetString(string json, string key, out string value)
        {
            value = null;
            var pattern = "\"" + key + "\"";
            var idx = IndexOfKey(json, pattern);
            if (idx < 0) return false;
            var i = idx + pattern.Length;
            while (i < json.Length && (json[i] == ':' || char.IsWhiteSpace(json[i]))) i++;
            if (i >= json.Length) return false;
            if (json[i] == '"')
            {
                i++;
                var sb = new StringBuilder();
                while (i < json.Length && json[i] != '"')
                {
                    if (json[i] == '\\' && i + 1 < json.Length)
                    {
                        sb.Append(json[i + 1]);
                        i += 2;
                        continue;
                    }
                    sb.Append(json[i]);
                    i++;
                }
                value = sb.ToString();
                return true;
            }
            // number / bare token — treat as string form
            var start = i;
            while (i < json.Length && json[i] != ',' && json[i] != '}' && !char.IsWhiteSpace(json[i]))
                i++;
            value = json.Substring(start, i - start);
            return value.Length > 0;
        }

        public static bool TryGetInt(string json, string key, out int value)
        {
            value = 0;
            if (!TryGetString(json, key, out var raw) || string.IsNullOrEmpty(raw))
                return false;
            return int.TryParse(raw, System.Globalization.NumberStyles.Integer,
                System.Globalization.CultureInfo.InvariantCulture, out value);
        }

        public static bool TryGetFloat(string json, string key, out float value)
        {
            value = 0f;
            if (!TryGetString(json, key, out var raw) || string.IsNullOrEmpty(raw))
                return false;
            return float.TryParse(raw, System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture, out value);
        }

        public static bool TryGetRawObject(string json, string key, out string raw)
        {
            raw = null;
            var pattern = "\"" + key + "\"";
            var idx = IndexOfKey(json, pattern);
            if (idx < 0) return false;
            var i = idx + pattern.Length;
            while (i < json.Length && (json[i] == ':' || char.IsWhiteSpace(json[i]))) i++;
            if (i >= json.Length || json[i] != '{') return false;
            var start = i;
            var depth = 0;
            for (; i < json.Length; i++)
            {
                var c = json[i];
                if (c == '"')
                {
                    i++;
                    while (i < json.Length && json[i] != '"')
                    {
                        if (json[i] == '\\') i++;
                        i++;
                    }
                    continue;
                }
                if (c == '{') depth++;
                else if (c == '}')
                {
                    depth--;
                    if (depth == 0)
                    {
                        raw = json.Substring(start, i - start + 1);
                        return true;
                    }
                }
            }
            return false;
        }

        public static bool TryGetRawArray(string json, string key, out string raw)
        {
            raw = null;
            var pattern = "\"" + key + "\"";
            var idx = IndexOfKey(json, pattern);
            if (idx < 0) return false;
            var i = idx + pattern.Length;
            while (i < json.Length && (json[i] == ':' || char.IsWhiteSpace(json[i]))) i++;
            if (i >= json.Length || json[i] != '[') return false;
            var start = i;
            var depth = 0;
            for (; i < json.Length; i++)
            {
                var c = json[i];
                if (c == '"')
                {
                    i++;
                    while (i < json.Length && json[i] != '"')
                    {
                        if (json[i] == '\\') i++;
                        i++;
                    }
                    continue;
                }
                if (c == '[') depth++;
                else if (c == ']')
                {
                    depth--;
                    if (depth == 0)
                    {
                        raw = json.Substring(start, i - start + 1);
                        return true;
                    }
                }
            }
            return false;
        }

        private static int IndexOfKey(string json, string quotedKey)
        {
            // Prefer top-level-ish match; simple IndexOf is enough for our flat envelopes.
            return json.IndexOf(quotedKey, StringComparison.Ordinal);
        }
    }
}
#endif
