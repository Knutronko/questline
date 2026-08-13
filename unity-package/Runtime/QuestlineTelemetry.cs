#if UNITY_EDITOR || QUESTLINE_DEV
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEngine;

namespace Questline.Companion
{
    /// <summary>
    /// Genre-agnostic thin gameplay telemetry (FP-G2). Games emit events; Python
    /// drains via hooks or imports the JSON spool. No game type names.
    /// </summary>
    public static class QuestlineTelemetry
    {
        public const int SchemaVersion = 1;
        public const int RingCapacity = 10000;
        public const int DrainBatch = 500;
        public const int FlushEvery = 25;

        static readonly object Gate = new object();
        static readonly List<TelEvent> Buffer = new List<TelEvent>(256);
        static TelemetryContext Ctx = new TelemetryContext();
        static bool Active;
        static float StartUnscaled;
        static int NextSeq = 1;
        static int Dropped;
        static int SinceFlush;
        static bool HooksRegistered;

        /// <summary>Ensure drain/status hooks exist. Safe to call more than once.</summary>
        public static void EnsureRegistered()
        {
            if (HooksRegistered)
            {
                return;
            }

            QuestlineHooks.Register<string>(
                "BeginTelemetrySession",
                json =>
                {
                    ApplyContextJson(json, reset: true);
                    return StatusJson();
                },
                feature: "telemetry",
                argName: "context_json");
            QuestlineHooks.Register<string>(
                "SetTelemetryContext",
                json =>
                {
                    ApplyContextJson(json, reset: false);
                    return StatusJson();
                },
                feature: "telemetry",
                argName: "context_json");
            QuestlineHooks.Register<string>(
                "EndTelemetrySession",
                outcome =>
                {
                    EndSession(outcome);
                    return StatusJson();
                },
                feature: "telemetry",
                argName: "outcome");
            QuestlineHooks.Register("DrainTelemetry", DrainJson, feature: "telemetry");
            QuestlineHooks.Register("TelemetryStatus", StatusJson, feature: "telemetry");
            HooksRegistered = true;
        }

        public static void BeginSession(TelemetryContext context)
        {
            EnsureRegistered();
            lock (Gate)
            {
                Ctx = context ?? new TelemetryContext();
                if (string.IsNullOrEmpty(Ctx.SessionId))
                {
                    Ctx.SessionId = Guid.NewGuid().ToString("N");
                }

                Buffer.Clear();
                NextSeq = 1;
                Dropped = 0;
                SinceFlush = 0;
                Active = true;
                StartUnscaled = Time.unscaledTime;
                Ctx.StartedAt = NowIso();
                Ctx.FinishedAt = null;
                Ctx.Outcome = null;
            }

            EmitLocked("session.start", PayloadStart(context));
            FlushSpool(force: true);
        }

        public static void SetContext(TelemetryContext patch)
        {
            if (patch == null)
            {
                return;
            }

            EnsureRegistered();
            lock (Gate)
            {
                MergeContext(patch);
            }
        }

        public static void EndSession(string outcome)
        {
            EnsureRegistered();
            var payload = new StringBuilder();
            payload.Append('{');
            AppendJsonString(payload, "outcome", string.IsNullOrEmpty(outcome) ? "unknown" : outcome);
            float duration;
            lock (Gate)
            {
                duration = Active ? Time.unscaledTime - StartUnscaled : 0f;
            }

            payload.Append(",\"duration_s\":");
            payload.Append(duration.ToString("G9", CultureInfo.InvariantCulture));
            payload.Append('}');
            Emit("session.end", payload.ToString());
            lock (Gate)
            {
                Ctx.Outcome = string.IsNullOrEmpty(outcome) ? "unknown" : outcome;
                Ctx.FinishedAt = NowIso();
                Active = false;
            }

            FlushSpool(force: true);
        }

        public static void Checkpoint(string label, int waveIndex = -1, string currenciesJson = null)
        {
            var sb = new StringBuilder();
            sb.Append('{');
            AppendJsonString(sb, "label", label ?? "");
            if (waveIndex >= 0)
            {
                sb.Append(",\"wave_index\":").Append(waveIndex);
            }

            if (!string.IsNullOrEmpty(currenciesJson))
            {
                sb.Append(",\"currencies\":").Append(currenciesJson);
            }

            sb.Append('}');
            Emit("session.checkpoint", sb.ToString());
        }

        public static void CurrencyEarned(string currencyId, float amount, float balanceAfter = float.NaN, string source = null)
        {
            Emit("currency.earned", CurrencyPayload(currencyId, amount, balanceAfter, "source", source));
        }

        public static void CurrencySpent(string currencyId, float amount, float balanceAfter = float.NaN, string sink = null)
        {
            Emit("currency.spent", CurrencyPayload(currencyId, amount, balanceAfter, "sink", sink));
        }

        public static void UnitDeployed(
            string unitId,
            float cost = float.NaN,
            string currencyId = null,
            int lane = -1,
            int slot = -1,
            string[] tags = null)
        {
            var sb = new StringBuilder();
            sb.Append('{');
            AppendJsonString(sb, "unit_id", unitId ?? "");
            if (!float.IsNaN(cost))
            {
                sb.Append(",\"cost\":").Append(cost.ToString("G9", CultureInfo.InvariantCulture));
            }

            if (!string.IsNullOrEmpty(currencyId))
            {
                sb.Append(',');
                AppendJsonString(sb, "currency_id", currencyId);
            }

            if (lane >= 0)
            {
                sb.Append(",\"lane\":").Append(lane);
            }

            if (slot >= 0)
            {
                sb.Append(",\"slot\":").Append(slot);
            }

            if (tags != null && tags.Length > 0)
            {
                sb.Append(",\"tags\":[");
                for (var i = 0; i < tags.Length; i++)
                {
                    if (i > 0) sb.Append(',');
                    sb.Append('"').Append(Escape(tags[i])).Append('"');
                }

                sb.Append(']');
            }

            sb.Append('}');
            Emit("unit.deployed", sb.ToString());
        }

        public static void CombatLeak(int waveIndex = -1, int lane = -1, string unitId = null)
        {
            Emit("combat.leak", LeakOrWavePayload(waveIndex, lane, unitId));
        }

        public static void WaveStarted(int waveIndex)
        {
            Emit("wave.started", "{\"wave_index\":" + waveIndex + "}");
        }

        public static void WaveCompleted(int waveIndex, float durationS = float.NaN, bool cleared = true)
        {
            var sb = new StringBuilder();
            sb.Append("{\"wave_index\":").Append(waveIndex);
            sb.Append(",\"cleared\":").Append(cleared ? "true" : "false");
            if (!float.IsNaN(durationS))
            {
                sb.Append(",\"duration_s\":").Append(durationS.ToString("G9", CultureInfo.InvariantCulture));
            }

            sb.Append('}');
            Emit("wave.completed", sb.ToString());
        }

        public static void SkillCast(string skillId, float cost = float.NaN, string currencyId = null, int waveIndex = -1)
        {
            var sb = new StringBuilder();
            sb.Append('{');
            AppendJsonString(sb, "skill_id", skillId ?? "");
            if (!float.IsNaN(cost))
            {
                sb.Append(",\"cost\":").Append(cost.ToString("G9", CultureInfo.InvariantCulture));
            }

            if (!string.IsNullOrEmpty(currencyId))
            {
                sb.Append(',');
                AppendJsonString(sb, "currency_id", currencyId);
            }

            if (waveIndex >= 0)
            {
                sb.Append(",\"wave_index\":").Append(waveIndex);
            }

            sb.Append('}');
            Emit("skill.cast", sb.ToString());
        }

        public static void RepairApplied(float cost = float.NaN, string currencyId = null, float amount = float.NaN)
        {
            var sb = new StringBuilder();
            sb.Append('{');
            var first = true;
            if (!float.IsNaN(cost))
            {
                sb.Append("\"cost\":").Append(cost.ToString("G9", CultureInfo.InvariantCulture));
                first = false;
            }

            if (!string.IsNullOrEmpty(currencyId))
            {
                if (!first) sb.Append(',');
                AppendJsonString(sb, "currency_id", currencyId);
                first = false;
            }

            if (!float.IsNaN(amount))
            {
                if (!first) sb.Append(',');
                sb.Append("\"amount\":").Append(amount.ToString("G9", CultureInfo.InvariantCulture));
            }

            if (first)
            {
                // empty object is valid for repair.applied
            }

            sb.Append('}');
            Emit("repair.applied", sb.ToString());
        }

        /// <summary>Escape hatch for extra / future event names (stored, not thin-rolled-up).</summary>
        public static void Emit(string name, string payloadJson = "{}")
        {
            EnsureRegistered();
            if (string.IsNullOrEmpty(name))
            {
                return;
            }

            EmitLocked(name, string.IsNullOrEmpty(payloadJson) ? "{}" : payloadJson);
        }

        static void EmitLocked(string name, string payloadJson)
        {
            lock (Gate)
            {
                if (!Active && name != "session.start")
                {
                    // Auto-start a session so late emits are not dropped on the floor.
                    Ctx.SessionId = string.IsNullOrEmpty(Ctx.SessionId)
                        ? Guid.NewGuid().ToString("N")
                        : Ctx.SessionId;
                    Active = true;
                    StartUnscaled = Time.unscaledTime;
                    if (string.IsNullOrEmpty(Ctx.StartedAt))
                    {
                        Ctx.StartedAt = NowIso();
                    }
                }

                var ev = new TelEvent
                {
                    Seq = NextSeq++,
                    T = Active ? Time.unscaledTime - StartUnscaled : 0f,
                    Name = name,
                    PayloadJson = payloadJson,
                };
                Buffer.Add(ev);
                while (Buffer.Count > RingCapacity)
                {
                    Buffer.RemoveAt(0);
                    Dropped++;
                }

                SinceFlush++;
                if (SinceFlush >= FlushEvery)
                {
                    SinceFlush = 0;
                    WriteSpoolUnlocked();
                }
            }
        }

        static string DrainJson()
        {
            EnsureRegistered();
            lock (Gate)
            {
                var take = Math.Min(DrainBatch, Buffer.Count);
                var sb = new StringBuilder();
                sb.Append("{\"dropped_count\":").Append(Dropped);
                sb.Append(",\"session\":");
                AppendSessionObject(sb);
                sb.Append(",\"events\":[");
                for (var i = 0; i < take; i++)
                {
                    if (i > 0) sb.Append(',');
                    AppendEvent(sb, Buffer[i]);
                }

                sb.Append("]}");
                if (take > 0)
                {
                    Buffer.RemoveRange(0, take);
                }

                return sb.ToString();
            }
        }

        static string StatusJson()
        {
            lock (Gate)
            {
                var sb = new StringBuilder();
                sb.Append("{\"buffer_count\":").Append(Buffer.Count);
                sb.Append(",\"dropped_count\":").Append(Dropped);
                sb.Append(",\"active\":").Append(Active ? "true" : "false");
                sb.Append(",\"session\":");
                AppendSessionObject(sb);
                sb.Append('}');
                return sb.ToString();
            }
        }

        static void FlushSpool(bool force)
        {
            lock (Gate)
            {
                if (force || SinceFlush > 0)
                {
                    SinceFlush = 0;
                    WriteSpoolUnlocked();
                }
            }
        }

        static void WriteSpoolUnlocked()
        {
            if (string.IsNullOrEmpty(Ctx.SessionId))
            {
                return;
            }

            try
            {
                var dir = Path.Combine(Application.persistentDataPath, "questline_telemetry");
                Directory.CreateDirectory(dir);
                var path = Path.Combine(dir, Ctx.SessionId + ".json");
                var sb = new StringBuilder();
                sb.Append("{\"schema_version\":").Append(SchemaVersion);
                sb.Append(",\"session\":");
                AppendSessionObject(sb);
                sb.Append(",\"events\":[");
                for (var i = 0; i < Buffer.Count; i++)
                {
                    if (i > 0) sb.Append(',');
                    AppendEvent(sb, Buffer[i]);
                }

                sb.Append("]}");
                File.WriteAllText(path, sb.ToString(), new UTF8Encoding(false));
            }
            catch (Exception ex)
            {
                Debug.LogWarning("[Questline] telemetry spool write failed: " + ex.Message);
            }
        }

        static void ApplyContextJson(string json, bool reset)
        {
            EnsureRegistered();
            var parsed = ParseContext(json);
            lock (Gate)
            {
                if (reset)
                {
                    BeginSessionUnlocked(parsed);
                }
                else
                {
                    MergeContext(parsed);
                }
            }

            if (reset)
            {
                EmitLocked("session.start", PayloadStart(parsed));
                FlushSpool(force: true);
            }
        }

        static void BeginSessionUnlocked(TelemetryContext context)
        {
            Ctx = context ?? new TelemetryContext();
            if (string.IsNullOrEmpty(Ctx.SessionId))
            {
                Ctx.SessionId = Guid.NewGuid().ToString("N");
            }

            Buffer.Clear();
            NextSeq = 1;
            Dropped = 0;
            SinceFlush = 0;
            Active = true;
            StartUnscaled = Time.unscaledTime;
            Ctx.StartedAt = NowIso();
            Ctx.FinishedAt = null;
            Ctx.Outcome = null;
        }

        static void MergeContext(TelemetryContext patch)
        {
            if (!string.IsNullOrEmpty(patch.SessionId)) Ctx.SessionId = patch.SessionId;
            if (!string.IsNullOrEmpty(patch.GameVersion)) Ctx.GameVersion = patch.GameVersion;
            if (!string.IsNullOrEmpty(patch.GitCommit)) Ctx.GitCommit = patch.GitCommit;
            if (!string.IsNullOrEmpty(patch.FeatureId)) Ctx.FeatureId = patch.FeatureId;
            if (!string.IsNullOrEmpty(patch.ConfigSnapshotId)) Ctx.ConfigSnapshotId = patch.ConfigSnapshotId;
            if (!string.IsNullOrEmpty(patch.PolicyId)) Ctx.PolicyId = patch.PolicyId;
            if (!string.IsNullOrEmpty(patch.Seed)) Ctx.Seed = patch.Seed;
            if (!string.IsNullOrEmpty(patch.LevelId)) Ctx.LevelId = patch.LevelId;
            if (!string.IsNullOrEmpty(patch.Mode)) Ctx.Mode = patch.Mode;
        }

        static TelemetryContext ParseContext(string json)
        {
            var ctx = new TelemetryContext();
            if (string.IsNullOrWhiteSpace(json))
            {
                return ctx;
            }

            ctx.SessionId = ExtractString(json, "id") ?? ExtractString(json, "session_id");
            ctx.GameVersion = ExtractString(json, "game_version");
            ctx.GitCommit = ExtractString(json, "git_commit");
            ctx.FeatureId = ExtractString(json, "feature_id");
            ctx.ConfigSnapshotId = ExtractString(json, "config_snapshot_id");
            ctx.PolicyId = ExtractString(json, "policy_id");
            ctx.Seed = ExtractString(json, "seed");
            ctx.LevelId = ExtractString(json, "level_id");
            ctx.Mode = ExtractString(json, "mode");
            return ctx;
        }

        static string ExtractString(string json, string key)
        {
            var needle = "\"" + key + "\"";
            var idx = json.IndexOf(needle, StringComparison.Ordinal);
            if (idx < 0)
            {
                return null;
            }

            var colon = json.IndexOf(':', idx + needle.Length);
            if (colon < 0)
            {
                return null;
            }

            var i = colon + 1;
            while (i < json.Length && char.IsWhiteSpace(json[i])) i++;
            if (i >= json.Length || json[i] == 'n')
            {
                return null;
            }

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

                return sb.ToString();
            }

            var start = i;
            while (i < json.Length && json[i] != ',' && json[i] != '}' && !char.IsWhiteSpace(json[i]))
            {
                i++;
            }

            var raw = json.Substring(start, i - start);
            return raw.Length == 0 ? null : raw;
        }

        static void AppendSessionObject(StringBuilder sb)
        {
            sb.Append('{');
            sb.Append("\"schema_version\":").Append(SchemaVersion);
            sb.Append(',');
            AppendJsonString(sb, "id", Ctx.SessionId ?? "");
            sb.Append(',');
            AppendJsonString(sb, "game_version", Ctx.GameVersion ?? "");
            AppendNullableString(sb, "git_commit", Ctx.GitCommit);
            AppendNullableString(sb, "feature_id", Ctx.FeatureId);
            AppendNullableString(sb, "config_snapshot_id", Ctx.ConfigSnapshotId);
            AppendNullableString(sb, "policy_id", Ctx.PolicyId);
            AppendNullableString(sb, "seed", Ctx.Seed);
            AppendNullableString(sb, "started_at", Ctx.StartedAt);
            AppendNullableString(sb, "finished_at", Ctx.FinishedAt);
            AppendNullableString(sb, "outcome", Ctx.Outcome);
            sb.Append(",\"source\":\"spool\"");
            sb.Append(",\"dropped_count\":").Append(Dropped);
            if (!string.IsNullOrEmpty(Ctx.LevelId) || !string.IsNullOrEmpty(Ctx.Mode))
            {
                // kept on events (session.start), not required on envelope
            }

            sb.Append('}');
        }

        static void AppendEvent(StringBuilder sb, TelEvent ev)
        {
            sb.Append("{\"seq\":").Append(ev.Seq);
            sb.Append(",\"t\":").Append(ev.T.ToString("G9", CultureInfo.InvariantCulture));
            sb.Append(',');
            AppendJsonString(sb, "name", ev.Name);
            sb.Append(",\"payload\":").Append(string.IsNullOrEmpty(ev.PayloadJson) ? "{}" : ev.PayloadJson);
            sb.Append('}');
        }

        static string PayloadStart(TelemetryContext context)
        {
            var sb = new StringBuilder();
            sb.Append('{');
            var first = true;
            if (context != null && !string.IsNullOrEmpty(context.LevelId))
            {
                AppendJsonString(sb, "level_id", context.LevelId);
                first = false;
            }

            if (context != null && !string.IsNullOrEmpty(context.Mode))
            {
                if (!first) sb.Append(',');
                AppendJsonString(sb, "mode", context.Mode);
            }

            sb.Append('}');
            return sb.ToString();
        }

        static string CurrencyPayload(string currencyId, float amount, float balanceAfter, string extraKey, string extraVal)
        {
            var sb = new StringBuilder();
            sb.Append('{');
            AppendJsonString(sb, "currency_id", currencyId ?? "");
            sb.Append(",\"amount\":").Append(amount.ToString("G9", CultureInfo.InvariantCulture));
            if (!float.IsNaN(balanceAfter))
            {
                sb.Append(",\"balance_after\":").Append(balanceAfter.ToString("G9", CultureInfo.InvariantCulture));
            }

            if (!string.IsNullOrEmpty(extraVal))
            {
                sb.Append(',');
                AppendJsonString(sb, extraKey, extraVal);
            }

            sb.Append('}');
            return sb.ToString();
        }

        static string LeakOrWavePayload(int waveIndex, int lane, string unitId)
        {
            var sb = new StringBuilder();
            sb.Append('{');
            var first = true;
            if (waveIndex >= 0)
            {
                sb.Append("\"wave_index\":").Append(waveIndex);
                first = false;
            }

            if (lane >= 0)
            {
                if (!first) sb.Append(',');
                sb.Append("\"lane\":").Append(lane);
                first = false;
            }

            if (!string.IsNullOrEmpty(unitId))
            {
                if (!first) sb.Append(',');
                AppendJsonString(sb, "unit_id", unitId);
            }

            sb.Append('}');
            return sb.ToString();
        }

        static void AppendJsonString(StringBuilder sb, string key, string value)
        {
            sb.Append('"').Append(key).Append("\":\"").Append(Escape(value)).Append('"');
        }

        static void AppendNullableString(StringBuilder sb, string key, string value)
        {
            sb.Append(",\"").Append(key).Append("\":");
            if (string.IsNullOrEmpty(value))
            {
                sb.Append("null");
            }
            else
            {
                sb.Append('"').Append(Escape(value)).Append('"');
            }
        }

        static string Escape(string value)
        {
            if (string.IsNullOrEmpty(value)) return "";
            return value.Replace("\\", "\\\\").Replace("\"", "\\\"");
        }

        static string NowIso()
        {
            return DateTime.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ", CultureInfo.InvariantCulture);
        }

        sealed class TelEvent
        {
            public int Seq;
            public float T;
            public string Name;
            public string PayloadJson;
        }
    }

    /// <summary>Session envelope. Null/empty fields are omitted or left unchanged on merge.</summary>
    public sealed class TelemetryContext
    {
        public string SessionId;
        public string GameVersion;
        public string GitCommit;
        public string FeatureId;
        public string ConfigSnapshotId;
        public string PolicyId;
        public string Seed;
        public string LevelId;
        public string Mode;
        public string StartedAt;
        public string FinishedAt;
        public string Outcome;
    }
}
#endif
