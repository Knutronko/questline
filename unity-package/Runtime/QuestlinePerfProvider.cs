using System.Globalization;
using System.Text;
using UnityEngine;
using UnityEngine.Profiling;

namespace Questline.Companion
{
    /// <summary>
    /// Editor / standalone (and optional device) perf counters for PerfProbe (phase-09 / QL-3).
    /// Registers the <c>GetPerfSample</c> hook returning JSON:
    /// <c>{"fps":60,"allocated_mb":12.5,"draw_calls":0}</c>.
    /// <c>draw_calls</c> is reserved (0 by default; no UnityEditor dependency in the Runtime asmdef).
    /// </summary>
    public sealed class QuestlinePerfProvider : MonoBehaviour
    {
        private static QuestlinePerfProvider _instance;
        private static bool _hookRegistered;

        private int _frames;
        private float _windowStart;
        private float _lastFps = 60f;

        /// <summary>
        /// Ensure a DontDestroyOnLoad sampler exists and <c>GetPerfSample</c> is registered.
        /// Safe to call from Wire bootstrap or game QL-3 Awake.
        /// </summary>
        public static QuestlinePerfProvider EnsureRegistered()
        {
            if (_instance == null)
            {
                var go = new GameObject("QuestlinePerfProvider");
                DontDestroyOnLoad(go);
                _instance = go.AddComponent<QuestlinePerfProvider>();
            }

            if (!_hookRegistered)
            {
                QuestlineHooks.Register(
                    "GetPerfSample",
                    () => _instance != null ? _instance.BuildSampleJson() : EmptySampleJson(),
                    feature: "perf");
                _hookRegistered = true;
            }

            return _instance;
        }

        private void Awake()
        {
            if (_instance != null && _instance != this)
            {
                Destroy(gameObject);
                return;
            }

            _instance = this;
            _windowStart = Time.unscaledTime;
            _frames = 0;
            EnsureRegistered();
        }

        private void Update()
        {
            _frames++;
            var now = Time.unscaledTime;
            var elapsed = now - _windowStart;
            if (elapsed >= 0.5f)
            {
                _lastFps = _frames / elapsed;
                _frames = 0;
                _windowStart = now;
            }
        }

        private void OnDestroy()
        {
            if (_instance == this)
                _instance = null;
        }

        private string BuildSampleJson()
        {
            var allocatedMb = Profiler.GetTotalAllocatedMemoryLong() / (1024.0 * 1024.0);
            var sb = new StringBuilder(96);
            sb.Append('{');
            AppendNumber(sb, "fps", _lastFps);
            sb.Append(',');
            AppendNumber(sb, "allocated_mb", allocatedMb);
            sb.Append(',');
            AppendNumber(sb, "draw_calls", 0);
            sb.Append('}');
            return sb.ToString();
        }

        private static string EmptySampleJson()
        {
            return "{\"fps\":0,\"allocated_mb\":0,\"draw_calls\":0}";
        }

        private static void AppendNumber(StringBuilder sb, string key, double value)
        {
            sb.Append('"').Append(key).Append("\":");
            sb.Append(value.ToString("G", CultureInfo.InvariantCulture));
        }

        private static void AppendNumber(StringBuilder sb, string key, int value)
        {
            sb.Append('"').Append(key).Append("\":");
            sb.Append(value.ToString(CultureInfo.InvariantCulture));
        }
    }
}
