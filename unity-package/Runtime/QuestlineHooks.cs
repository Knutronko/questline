using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using UnityEngine;

namespace Questline.Companion
{
    /// <summary>
    /// Typed debug-hook registry exposed to Questline via AltTester CallStaticMethod.
    /// Games register hooks at boot; Python calls InvokeHook / GetManifestJson.
    /// </summary>
    public static class QuestlineHooks
    {
        private static readonly Dictionary<string, HookRegistration> Hooks =
            new Dictionary<string, HookRegistration>(StringComparer.Ordinal);

        /// <summary>Register a zero-arg hook.</summary>
        public static void Register(string name, Func<object> handler, bool causesSoftReload = false, string feature = null)
        {
            RegisterInternal(name, causesSoftReload, feature, Array.Empty<HookArgSpec>(), args => handler());
        }

        /// <summary>Register a one-arg hook.</summary>
        public static void Register<T1>(string name, Func<T1, object> handler, bool causesSoftReload = false, string feature = null, string argName = "arg0")
        {
            RegisterInternal(
                name,
                causesSoftReload,
                feature,
                new[] { new HookArgSpec(argName, TypeLabel(typeof(T1))) },
                args => handler(ConvertArg<T1>(args, 0)));
        }

        /// <summary>Register a two-arg hook.</summary>
        public static void Register<T1, T2>(
            string name,
            Func<T1, T2, object> handler,
            bool causesSoftReload = false,
            string feature = null,
            string arg0Name = "arg0",
            string arg1Name = "arg1")
        {
            RegisterInternal(
                name,
                causesSoftReload,
                feature,
                new[]
                {
                    new HookArgSpec(arg0Name, TypeLabel(typeof(T1))),
                    new HookArgSpec(arg1Name, TypeLabel(typeof(T2))),
                },
                args => handler(ConvertArg<T1>(args, 0), ConvertArg<T2>(args, 1)));
        }

        /// <summary>Register a void zero-arg hook (returns null JSON).</summary>
        public static void RegisterAction(string name, Action handler, bool causesSoftReload = false, string feature = null)
        {
            Register(name, () =>
            {
                handler();
                return null;
            }, causesSoftReload, feature);
        }

        /// <summary>Clear all registrations (Editor tests / soft-reload re-init).</summary>
        public static void Clear()
        {
            Hooks.Clear();
        }

        /// <summary>
        /// Machine-readable registry dump for feature-scan diffs.
        /// Shape: {"hooks":[{"name":"...","args":[{"name":"...","type":"..."}],"causesSoftReload":false,"feature":null}]}
        /// </summary>
        public static string GetManifestJson()
        {
            var sb = new StringBuilder();
            sb.Append("{\"hooks\":[");
            var first = true;
            foreach (var pair in Hooks)
            {
                if (!first) sb.Append(',');
                first = false;
                var reg = pair.Value;
                sb.Append('{');
                AppendJsonString(sb, "name", reg.Name);
                sb.Append(",\"args\":[");
                for (var i = 0; i < reg.Args.Length; i++)
                {
                    if (i > 0) sb.Append(',');
                    sb.Append('{');
                    AppendJsonString(sb, "name", reg.Args[i].Name);
                    sb.Append(',');
                    AppendJsonString(sb, "type", reg.Args[i].Type);
                    sb.Append('}');
                }
                sb.Append("],\"causesSoftReload\":");
                sb.Append(reg.CausesSoftReload ? "true" : "false");
                if (!string.IsNullOrEmpty(reg.Feature))
                {
                    sb.Append(',');
                    AppendJsonString(sb, "feature", reg.Feature);
                }
                sb.Append('}');
            }
            sb.Append("]}");
            return sb.ToString();
        }

        /// <summary>
        /// Invoke a registered hook by name. argsJson is a JSON array (e.g. [1,"gold"]).
        /// Returns a JSON-encoded result (null → empty string).
        /// </summary>
        public static string InvokeHook(string name, string argsJson)
        {
            if (string.IsNullOrEmpty(name))
                throw new ArgumentException("hook name must be non-empty", nameof(name));
            if (!Hooks.TryGetValue(name, out var reg))
                throw new InvalidOperationException($"unknown questline hook: {name}");

            var args = ParseArgsArray(argsJson);
            object result;
            try
            {
                // When CausesSoftReload is true, the *handler* is responsible for the reload
                // (e.g. SceneManager.LoadScene). Python AltTesterDriver re-handshakes after return.
                result = reg.Handler(args);
            }
            catch (Exception ex)
            {
                Debug.LogException(ex);
                throw;
            }

            return EncodeResult(result);
        }

        private static void RegisterInternal(
            string name,
            bool causesSoftReload,
            string feature,
            HookArgSpec[] args,
            Func<object[], object> handler)
        {
            if (string.IsNullOrEmpty(name))
                throw new ArgumentException("hook name must be non-empty", nameof(name));
            if (handler == null)
                throw new ArgumentNullException(nameof(handler));
            Hooks[name] = new HookRegistration(name, args, causesSoftReload, feature, handler);
        }

        private static string TypeLabel(Type t)
        {
            if (t == typeof(int) || t == typeof(Int32)) return "int";
            if (t == typeof(long) || t == typeof(Int64)) return "long";
            if (t == typeof(float) || t == typeof(Single)) return "float";
            if (t == typeof(double) || t == typeof(Double)) return "double";
            if (t == typeof(bool) || t == typeof(Boolean)) return "bool";
            if (t == typeof(string) || t == typeof(String)) return "string";
            return t.FullName ?? t.Name;
        }

        private static T ConvertArg<T>(object[] args, int index)
        {
            if (args == null || index >= args.Length)
                throw new ArgumentException($"hook expected argument at index {index}");
            var value = args[index];
            if (value is T typed)
                return typed;
            if (value == null)
                return default;
            try
            {
                return (T)Convert.ChangeType(value, typeof(T), CultureInfo.InvariantCulture);
            }
            catch (Exception ex)
            {
                throw new ArgumentException(
                    $"cannot convert hook arg[{index}] ({value}) to {typeof(T).Name}", ex);
            }
        }

        private static object[] ParseArgsArray(string argsJson)
        {
            if (string.IsNullOrWhiteSpace(argsJson) || argsJson.Trim() == "[]")
                return Array.Empty<object>();

            // Minimal JSON array parser for scalars: strings, numbers, bools, null.
            var text = argsJson.Trim();
            if (text[0] != '[' || text[text.Length - 1] != ']')
                throw new ArgumentException("argsJson must be a JSON array", nameof(argsJson));

            var inner = text.Substring(1, text.Length - 2).Trim();
            if (inner.Length == 0)
                return Array.Empty<object>();

            var list = new List<object>();
            var i = 0;
            while (i < inner.Length)
            {
                while (i < inner.Length && (inner[i] == ',' || char.IsWhiteSpace(inner[i])))
                    i++;
                if (i >= inner.Length) break;

                if (inner[i] == '"')
                {
                    i++;
                    var sb = new StringBuilder();
                    while (i < inner.Length && inner[i] != '"')
                    {
                        if (inner[i] == '\\' && i + 1 < inner.Length)
                        {
                            sb.Append(inner[i + 1]);
                            i += 2;
                            continue;
                        }
                        sb.Append(inner[i]);
                        i++;
                    }
                    if (i >= inner.Length || inner[i] != '"')
                        throw new ArgumentException("unterminated string in argsJson");
                    i++;
                    list.Add(sb.ToString());
                }
                else if (inner.Length >= i + 4 && string.Compare(inner, i, "true", 0, 4, StringComparison.OrdinalIgnoreCase) == 0)
                {
                    list.Add(true);
                    i += 4;
                }
                else if (inner.Length >= i + 5 && string.Compare(inner, i, "false", 0, 5, StringComparison.OrdinalIgnoreCase) == 0)
                {
                    list.Add(false);
                    i += 5;
                }
                else if (inner.Length >= i + 4 && string.Compare(inner, i, "null", 0, 4, StringComparison.OrdinalIgnoreCase) == 0)
                {
                    list.Add(null);
                    i += 4;
                }
                else
                {
                    var start = i;
                    while (i < inner.Length && inner[i] != ',' && !char.IsWhiteSpace(inner[i]))
                        i++;
                    var num = inner.Substring(start, i - start);
                    if (num.IndexOf('.') >= 0 || num.IndexOf('e') >= 0 || num.IndexOf('E') >= 0)
                        list.Add(double.Parse(num, CultureInfo.InvariantCulture));
                    else
                        list.Add(long.Parse(num, CultureInfo.InvariantCulture));
                }
            }
            return list.ToArray();
        }

        private static string EncodeResult(object result)
        {
            if (result == null) return "";
            if (result is string s) return "\"" + Escape(s) + "\"";
            if (result is bool b) return b ? "true" : "false";
            if (result is IFormattable fmt)
                return fmt.ToString(null, CultureInfo.InvariantCulture);
            return "\"" + Escape(result.ToString()) + "\"";
        }

        private static void AppendJsonString(StringBuilder sb, string key, string value)
        {
            sb.Append('"').Append(key).Append("\":\"").Append(Escape(value)).Append('"');
        }

        private static string Escape(string value)
        {
            if (string.IsNullOrEmpty(value)) return "";
            return value.Replace("\\", "\\\\").Replace("\"", "\\\"");
        }

        private sealed class HookRegistration
        {
            public HookRegistration(
                string name,
                HookArgSpec[] args,
                bool causesSoftReload,
                string feature,
                Func<object[], object> handler)
            {
                Name = name;
                Args = args;
                CausesSoftReload = causesSoftReload;
                Feature = feature;
                Handler = handler;
            }

            public string Name { get; }
            public HookArgSpec[] Args { get; }
            public bool CausesSoftReload { get; }
            public string Feature { get; }
            public Func<object[], object> Handler { get; }
        }

        private readonly struct HookArgSpec
        {
            public HookArgSpec(string name, string type)
            {
                Name = name;
                Type = type;
            }

            public string Name { get; }
            public string Type { get; }
        }
    }
}
