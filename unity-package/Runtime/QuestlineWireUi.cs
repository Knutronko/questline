#if UNITY_EDITOR || QUESTLINE_DEV
using System;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.SceneManagement;
using UnityEngine.UI;
#if UNITY_TMP || UNITY_TEXTMESHPRO
using TMPro;
#endif

namespace Questline.Companion
{
    /// <summary>
    /// Wire v2 UI ops (ADR-0008): hierarchy / find / find_all / tap / screenshot.
    /// Bound depth/node caps; stable ids = GameObject.GetInstanceID().
    /// </summary>
    internal static class QuestlineWireUi
    {
        public const int DefaultMaxDepth = 32;
        public const int DefaultMaxNodes = 500;

        public static string HierarchyResult(string paramsJson)
        {
            var maxDepth = WireJson.TryGetInt(paramsJson, "max_depth", out var md) ? md : DefaultMaxDepth;
            var maxNodes = WireJson.TryGetInt(paramsJson, "max_nodes", out var mn) ? mn : DefaultMaxNodes;
            if (maxDepth < 0) maxDepth = 0;
            if (maxNodes < 1) maxNodes = 1;

            var scene = SceneManager.GetActiveScene().name ?? "";
            var counter = new Counter();
            var roots = new List<string>();
            var rootsGo = UnityEngine.Object.FindObjectsOfType<Transform>();
            // Prefer scene roots (no parent) to avoid duplicating the whole tree.
            var seen = new HashSet<int>();
            foreach (var t in rootsGo)
            {
                if (t == null || t.parent != null) continue;
                if (!t.gameObject.activeInHierarchy) continue;
                var node = BuildNode(t, 0, maxDepth, maxNodes, counter, seen);
                if (node != null) roots.Add(node);
            }

            var sb = new StringBuilder();
            sb.Append('{');
            sb.Append("\"scene\":\"").Append(WireJson.Escape(scene)).Append("\",");
            sb.Append("\"truncated\":").Append(counter.Truncated ? "true" : "false").Append(',');
            sb.Append("\"node_count\":").Append(counter.Count).Append(',');
            sb.Append("\"roots\":[");
            for (var i = 0; i < roots.Count; i++)
            {
                if (i > 0) sb.Append(',');
                sb.Append(roots[i]);
            }
            sb.Append("]}");
            return sb.ToString();
        }

        public static string FindResult(string paramsJson, bool all)
        {
            if (!WireJson.TryGetString(paramsJson, "by", out var by) || string.IsNullOrEmpty(by))
                throw new ArgumentException("find requires params.by");
            if (!WireJson.TryGetString(paramsJson, "value", out var value) || string.IsNullOrEmpty(value))
                throw new ArgumentException("find requires params.value");
            string scope = null;
            WireJson.TryGetString(paramsJson, "scope", out scope);
            if (string.IsNullOrEmpty(scope)) scope = null;

            var matches = Query(by, value, scope);
            if (all)
            {
                var sb = new StringBuilder();
                sb.Append("{\"elements\":[");
                for (var i = 0; i < matches.Count; i++)
                {
                    if (i > 0) sb.Append(',');
                    sb.Append(ElementJson(matches[i]));
                }
                sb.Append("]}");
                return sb.ToString();
            }

            if (matches.Count == 0)
                throw new ElementNotFoundException($"element not found: {by}={value}");
            return "{\"element\":" + ElementJson(matches[0]) + "}";
        }

        public static string TapResult(string paramsJson)
        {
            if (WireJson.TryGetString(paramsJson, "element_id", out var eid) && !string.IsNullOrEmpty(eid))
            {
                if (!TryResolveId(eid, out var go) || go == null || !go.activeInHierarchy)
                    throw new ElementNotFoundException($"tap target not found: {eid}");
                if (!go.activeSelf)
                    throw new ElementNotFoundException($"tap target disabled: {eid}");
                PerformTapOnGameObject(go);
                return "{\"ok\":true}";
            }

            if (WireJson.TryGetRawObject(paramsJson, "point", out var pointJson))
            {
                if (!WireJson.TryGetFloat(pointJson, "x", out var x) ||
                    !WireJson.TryGetFloat(pointJson, "y", out var y))
                    throw new ArgumentException("tap point requires numeric x/y");
                PerformScreenTap(new Vector2(x, y));
                return "{\"ok\":true}";
            }

            throw new ArgumentException("tap requires element_id or point");
        }

        public static string ScreenshotResult()
        {
            Texture2D tex = null;
            try
            {
                tex = ScreenCapture.CaptureScreenshotAsTexture();
                if (tex == null)
                    throw new InvalidOperationException("screenshot capture returned null texture");
                var png = tex.EncodeToPNG();
                if (png == null || png.Length == 0)
                    throw new InvalidOperationException("screenshot returned empty PNG payload");
                var b64 = Convert.ToBase64String(png);
                return "{\"png_base64\":\"" + b64 + "\"}";
            }
            finally
            {
                if (tex != null)
                    UnityEngine.Object.Destroy(tex);
            }
        }

        private static List<Transform> Query(string by, string value, string scope)
        {
            var results = new List<Transform>();
            var all = UnityEngine.Object.FindObjectsOfType<Transform>();
            foreach (var t in all)
            {
                if (t == null || !t.gameObject.activeInHierarchy) continue;
                var path = HierarchyPath(t);
                if (!string.IsNullOrEmpty(scope))
                {
                    var idStr = t.gameObject.GetInstanceID().ToString();
                    if (scope != path && scope != idStr && scope != t.name &&
                        path.IndexOf(scope, StringComparison.Ordinal) < 0)
                        continue;
                }
                if (Matches(t, by, value, path))
                    results.Add(t);
            }
            return results;
        }

        private static bool Matches(Transform t, string by, string value, string path)
        {
            switch (by)
            {
                case "id":
                    return t.gameObject.GetInstanceID().ToString() == value;
                case "name":
                    return t.name == value;
                case "path":
                    return path == value || path.EndsWith(value, StringComparison.Ordinal);
                case "text":
                    return ReadText(t) == value;
                case "component":
                    return HasComponentNamed(t.gameObject, value);
                default:
                    throw new ArgumentException($"unsupported locator strategy: {by}");
            }
        }

        private static string ReadText(Transform t)
        {
            var ugui = t.GetComponent<Text>();
            if (ugui != null) return ugui.text ?? "";
#if UNITY_TMP || UNITY_TEXTMESHPRO
            var tmp = t.GetComponent<TMP_Text>();
            if (tmp != null) return tmp.text ?? "";
#endif
            // Best-effort: scan children one level for a Text.
            for (var i = 0; i < t.childCount; i++)
            {
                var child = t.GetChild(i);
                var ct = child.GetComponent<Text>();
                if (ct != null) return ct.text ?? "";
#if UNITY_TMP || UNITY_TEXTMESHPRO
                var ctmp = child.GetComponent<TMP_Text>();
                if (ctmp != null) return ctmp.text ?? "";
#endif
            }
            return "";
        }

        private static bool HasComponentNamed(GameObject go, string typeName)
        {
            foreach (var c in go.GetComponents<Component>())
            {
                if (c == null) continue;
                var n = c.GetType().Name;
                if (n == typeName || c.GetType().FullName == typeName)
                    return true;
            }
            return false;
        }

        private static string BuildNode(
            Transform t,
            int depth,
            int maxDepth,
            int maxNodes,
            Counter counter,
            HashSet<int> seen)
        {
            if (t == null) return null;
            var id = t.gameObject.GetInstanceID();
            if (!seen.Add(id)) return null;
            if (counter.Count >= maxNodes)
            {
                counter.Truncated = true;
                return null;
            }
            if (depth > maxDepth)
            {
                counter.Truncated = true;
                return null;
            }

            counter.Count++;
            var childrenJson = new List<string>();
            if (depth < maxDepth)
            {
                for (var i = 0; i < t.childCount; i++)
                {
                    var child = t.GetChild(i);
                    if (child == null || !child.gameObject.activeInHierarchy) continue;
                    var childJson = BuildNode(child, depth + 1, maxDepth, maxNodes, counter, seen);
                    if (childJson != null) childrenJson.Add(childJson);
                    if (counter.Truncated && counter.Count >= maxNodes) break;
                }
            }
            else if (t.childCount > 0)
            {
                counter.Truncated = true;
            }

            var sb = new StringBuilder();
            sb.Append("{\"element\":").Append(ElementJson(t)).Append(",\"children\":[");
            for (var i = 0; i < childrenJson.Count; i++)
            {
                if (i > 0) sb.Append(',');
                sb.Append(childrenJson[i]);
            }
            sb.Append("]}");
            return sb.ToString();
        }

        private static string ElementJson(Transform t)
        {
            var go = t.gameObject;
            var path = HierarchyPath(t);
            var text = ReadText(t);
            var component = PrimaryComponentName(go);
            var bounds = BoundsArray(go);
            var sb = new StringBuilder();
            sb.Append('{');
            sb.Append("\"id\":\"").Append(WireJson.Escape(go.GetInstanceID().ToString())).Append("\",");
            sb.Append("\"name\":\"").Append(WireJson.Escape(go.name)).Append("\",");
            sb.Append("\"path\":\"").Append(WireJson.Escape(path)).Append("\",");
            sb.Append("\"text\":\"").Append(WireJson.Escape(text)).Append("\",");
            sb.Append("\"visible\":").Append(go.activeInHierarchy ? "true" : "false").Append(',');
            sb.Append("\"enabled\":").Append(go.activeSelf ? "true" : "false");
            if (!string.IsNullOrEmpty(component))
                sb.Append(",\"component\":\"").Append(WireJson.Escape(component)).Append('"');
            if (bounds != null)
                sb.Append(",\"bounds\":").Append(bounds);
            sb.Append('}');
            return sb.ToString();
        }

        private static string PrimaryComponentName(GameObject go)
        {
            foreach (var c in go.GetComponents<Component>())
            {
                if (c == null || c is Transform) continue;
                return c.GetType().Name;
            }
            return "Transform";
        }

        private static string BoundsArray(GameObject go)
        {
            var rt = go.GetComponent<RectTransform>();
            if (rt != null)
            {
                var corners = new Vector3[4];
                rt.GetWorldCorners(corners);
                var min = corners[0];
                var max = corners[2];
                // Screen space if possible.
                var cam = Camera.main;
                Vector2 sMin, sMax;
                if (cam != null)
                {
                    sMin = RectTransformUtility.WorldToScreenPoint(cam, min);
                    sMax = RectTransformUtility.WorldToScreenPoint(cam, max);
                }
                else
                {
                    sMin = new Vector2(min.x, min.y);
                    sMax = new Vector2(max.x, max.y);
                }
                var x = Math.Min(sMin.x, sMax.x);
                var y = Math.Min(sMin.y, sMax.y);
                var w = Math.Abs(sMax.x - sMin.x);
                var h = Math.Abs(sMax.y - sMin.y);
                return string.Format(
                    System.Globalization.CultureInfo.InvariantCulture,
                    "[{0},{1},{2},{3}]", x, y, w, h);
            }
            return null;
        }

        private static string HierarchyPath(Transform t)
        {
            var parts = new List<string>();
            var cur = t;
            while (cur != null)
            {
                parts.Add(cur.name);
                cur = cur.parent;
            }
            parts.Reverse();
            return "/" + string.Join("/", parts.ToArray());
        }

        private static bool TryResolveId(string eid, out GameObject go)
        {
            go = null;
            if (!int.TryParse(eid, out var instanceId)) return false;
            var all = UnityEngine.Object.FindObjectsOfType<Transform>();
            foreach (var t in all)
            {
                if (t != null && t.gameObject.GetInstanceID() == instanceId)
                {
                    go = t.gameObject;
                    return true;
                }
            }
            return false;
        }

        private static void PerformTapOnGameObject(GameObject go)
        {
            var graphic = go.GetComponent<Graphic>();
            if (graphic != null)
            {
                var ped = new PointerEventData(EventSystem.current != null
                    ? EventSystem.current
                    : null)
                {
                    button = PointerEventData.InputButton.Left,
                };
                ExecuteEvents.Execute(go, ped, ExecuteEvents.pointerClickHandler);
                ExecuteEvents.Execute(go, ped, ExecuteEvents.pointerDownHandler);
                ExecuteEvents.Execute(go, ped, ExecuteEvents.pointerUpHandler);
                return;
            }

            // Best-effort: screen-center of RectTransform, else zero.
            var rt = go.GetComponent<RectTransform>();
            if (rt != null)
            {
                var corners = new Vector3[4];
                rt.GetWorldCorners(corners);
                var mid = (corners[0] + corners[2]) * 0.5f;
                var cam = Camera.main;
                Vector2 screen = cam != null
                    ? (Vector2)RectTransformUtility.WorldToScreenPoint(cam, mid)
                    : new Vector2(mid.x, mid.y);
                PerformScreenTap(screen);
            }
        }

        private static void PerformScreenTap(Vector2 screen)
        {
            if (EventSystem.current == null) return;
            var ped = new PointerEventData(EventSystem.current)
            {
                position = screen,
                button = PointerEventData.InputButton.Left,
            };
            var results = new List<RaycastResult>();
            EventSystem.current.RaycastAll(ped, results);
            if (results.Count == 0) return;
            var target = results[0].gameObject;
            ExecuteEvents.Execute(target, ped, ExecuteEvents.pointerClickHandler);
            ExecuteEvents.ExecuteHierarchy(target, ped, ExecuteEvents.pointerClickHandler);
        }

        private sealed class Counter
        {
            public int Count;
            public bool Truncated;
        }

        internal sealed class ElementNotFoundException : Exception
        {
            public ElementNotFoundException(string message) : base(message) { }
        }
    }
}
#endif
