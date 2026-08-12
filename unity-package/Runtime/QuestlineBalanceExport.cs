#if UNITY_EDITOR || QUESTLINE_DEV
using System;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text;
using UnityEngine;
#if UNITY_EDITOR
using UnityEditor;
#endif

namespace Questline.Companion
{
    /// <summary>
    /// Genre-agnostic balance SO exporter for GameLens (FP-G1).
    /// The game supplies a JSON manifest (QL-5); this walks listed assets and writes
    /// a normalized balance_snapshot.json. No game-specific type names.
    /// </summary>
    public static class QuestlineBalanceExport
    {
        const int SchemaVersion = 1;

        [Serializable]
        public class ManifestDto
        {
            public int schema_version = 1;
            public ManifestEntryDto[] entries;
            public SupplementaryDto[] supplementary;
        }

        [Serializable]
        public class ManifestEntryDto
        {
            public string id;
            public string system;
            public string asset_path;
            public string source_file;
            public string kind = "config";
        }

        [Serializable]
        public class SupplementaryDto
        {
            public string kind;
            public string path;
        }

#if UNITY_EDITOR
        [MenuItem("Questline/Export Balance Snapshot")]
        public static void MenuExport()
        {
            var manifestPath = EditorUtility.OpenFilePanel(
                "GameLens balance manifest",
                Application.dataPath,
                "json");
            if (string.IsNullOrEmpty(manifestPath))
            {
                return;
            }

            var outPath = EditorUtility.SaveFilePanel(
                "Write balance_snapshot.json",
                Directory.GetParent(Application.dataPath) != null
                    ? Directory.GetParent(Application.dataPath).FullName
                    : Application.dataPath,
                "balance_snapshot.json",
                "json");
            if (string.IsNullOrEmpty(outPath))
            {
                return;
            }

            var gameVersion = PlayerSettings.bundleVersion;
            try
            {
                ExportFromManifest(manifestPath, outPath, gameVersion, null, null);
                EditorUtility.RevealInFinder(outPath);
                Debug.Log("[Questline] GameLens snapshot written: " + outPath);
            }
            catch (Exception ex)
            {
                Debug.LogError("[Questline] GameLens export failed: " + ex.Message);
                EditorUtility.DisplayDialog("Questline GameLens", ex.Message, "OK");
            }
        }
#endif

        /// <summary>
        /// Export balance snapshot from a manifest JSON path.
        /// Missing assets raise clear errors (no silent skip).
        /// </summary>
        public static void ExportFromManifest(
            string manifestPath,
            string outputPath,
            string gameVersion,
            string gitCommit,
            string featureId)
        {
            if (string.IsNullOrWhiteSpace(manifestPath) || !File.Exists(manifestPath))
            {
                throw new FileNotFoundException("manifest not found: " + manifestPath);
            }

            if (string.IsNullOrWhiteSpace(gameVersion))
            {
                throw new ArgumentException("gameVersion is required", "gameVersion");
            }

            var manifestJson = File.ReadAllText(manifestPath, Encoding.UTF8);
            var manifest = JsonUtility.FromJson<ManifestDto>(manifestJson);
            if (manifest == null)
            {
                throw new InvalidOperationException("failed to parse manifest: " + manifestPath);
            }

            if (manifest.schema_version != SchemaVersion)
            {
                throw new InvalidOperationException(
                    "unsupported manifest schema_version=" + manifest.schema_version
                    + " (expected " + SchemaVersion + ")");
            }

            if (manifest.entries == null || manifest.entries.Length == 0)
            {
                throw new InvalidOperationException("manifest.entries must be non-empty");
            }

            var sb = new StringBuilder();
            sb.Append("{\n");
            sb.Append("  \"schema_version\": ").Append(SchemaVersion).Append(",\n");
            sb.Append("  \"meta\": {\n");
            AppendJsonString(sb, "    ", "game_version", gameVersion, true);
            AppendJsonString(sb, "    ", "git_commit", gitCommit, true);
            AppendJsonString(sb, "    ", "feature_id", featureId, true);
            AppendJsonString(sb, "    ", "captured_at", DateTime.UtcNow.ToString("o"), true);
            AppendJsonString(sb, "    ", "manifest_path", manifestPath, false);
            sb.Append("\n  },\n");
            sb.Append("  \"entities\": {\n");

            for (var i = 0; i < manifest.entries.Length; i++)
            {
                var entry = manifest.entries[i];
                if (entry == null || string.IsNullOrWhiteSpace(entry.id))
                {
                    throw new InvalidOperationException(
                        "manifest.entries[" + i + "].id is required");
                }

                if (string.IsNullOrWhiteSpace(entry.system))
                {
                    throw new InvalidOperationException(
                        "manifest entry " + entry.id + ": system is required");
                }

                if (string.IsNullOrWhiteSpace(entry.asset_path))
                {
                    throw new InvalidOperationException(
                        "manifest entry " + entry.id
                        + ": asset_path is required for Editor export");
                }

#if UNITY_EDITOR
                var so = AssetDatabase.LoadAssetAtPath<ScriptableObject>(entry.asset_path);
                if (so == null)
                {
                    throw new FileNotFoundException(
                        "unknown or missing ScriptableObject for entry "
                        + entry.id + ": " + entry.asset_path);
                }

                var fieldsJson = SerializeObjectFields(so);
#else
                throw new InvalidOperationException(
                    "QuestlineBalanceExport.ExportFromManifest requires UNITY_EDITOR");
#endif
                sb.Append("    ").Append(Quote(entry.id)).Append(": {\n");
                AppendJsonString(sb, "      ", "id", entry.id, true);
                AppendJsonString(sb, "      ", "system", entry.system, true);
                AppendJsonString(
                    sb,
                    "      ",
                    "kind",
                    string.IsNullOrEmpty(entry.kind) ? "config" : entry.kind,
                    true);
                sb.Append("      \"fields\": ").Append(fieldsJson).Append('\n');
                sb.Append("    }");
                if (i < manifest.entries.Length - 1)
                {
                    sb.Append(',');
                }

                sb.Append('\n');
            }

            sb.Append("  },\n");
            sb.Append("  \"supplementary\": [\n");
            if (manifest.supplementary != null)
            {
                for (var i = 0; i < manifest.supplementary.Length; i++)
                {
                    var s = manifest.supplementary[i];
                    if (s == null)
                    {
                        continue;
                    }

                    sb.Append("    {");
                    sb.Append("\"kind\":").Append(Quote(s.kind ?? "markdown")).Append(',');
                    sb.Append("\"path\":").Append(Quote(s.path ?? ""));
                    sb.Append('}');
                    if (i < manifest.supplementary.Length - 1)
                    {
                        sb.Append(',');
                    }

                    sb.Append('\n');
                }
            }

            sb.Append("  ]\n");
            sb.Append("}\n");

            var dir = Path.GetDirectoryName(outputPath);
            if (!string.IsNullOrEmpty(dir))
            {
                Directory.CreateDirectory(dir);
            }

            // Encoding.UTF8 emits a BOM; Python json.loads(utf-8) rejects it.
            File.WriteAllText(outputPath, sb.ToString(), new UTF8Encoding(false));
        }

        static string SerializeObjectFields(UnityEngine.Object target)
        {
            var sb = new StringBuilder();
            sb.Append("{\n");
            var type = target.GetType();
            var fields = type.GetFields(
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
            var first = true;
            foreach (var field in fields)
            {
                if (field.IsNotSerialized)
                {
                    continue;
                }

                if (!field.IsPublic && field.GetCustomAttribute<SerializeField>() == null)
                {
                    continue;
                }

                if (!first)
                {
                    sb.Append(",\n");
                }

                first = false;
                sb.Append("        ").Append(Quote(field.Name)).Append(": ");
                AppendValue(sb, field.GetValue(target), 0);
            }

            sb.Append('\n').Append("      }");
            return sb.ToString();
        }

        static void AppendValue(StringBuilder sb, object value, int depth)
        {
            if (value == null)
            {
                sb.Append("{\"type\":\"null\",\"value\":null}");
                return;
            }

            if (value is bool)
            {
                sb.Append("{\"type\":\"bool\",\"value\":")
                    .Append((bool)value ? "true" : "false")
                    .Append('}');
                return;
            }

            if (IsNumeric(value))
            {
                sb.Append("{\"type\":\"number\",\"value\":")
                    .Append(Convert.ToDouble(value, CultureInfo.InvariantCulture)
                        .ToString("G17", CultureInfo.InvariantCulture))
                    .Append('}');
                return;
            }

            if (value is string)
            {
                sb.Append("{\"type\":\"string\",\"value\":")
                    .Append(Quote((string)value))
                    .Append('}');
                return;
            }

            var curve = value as AnimationCurve;
            if (curve != null)
            {
                sb.Append("{\"type\":\"curve\",\"points\":[");
                for (var i = 0; i < curve.length; i++)
                {
                    var k = curve[i];
                    if (i > 0)
                    {
                        sb.Append(',');
                    }

                    sb.Append('[')
                        .Append(k.time.ToString("G9", CultureInfo.InvariantCulture))
                        .Append(',')
                        .Append(k.value.ToString("G9", CultureInfo.InvariantCulture))
                        .Append(']');
                }

                sb.Append("]}");
                return;
            }

            if (value is UnityEngine.Object)
            {
                sb.Append("{\"type\":\"string\",\"value\":")
                    .Append(Quote(value.ToString()))
                    .Append('}');
                return;
            }

            var type = value.GetType();
            if (type.IsEnum)
            {
                sb.Append("{\"type\":\"string\",\"value\":")
                    .Append(Quote(value.ToString()))
                    .Append('}');
                return;
            }

            var list = value as System.Collections.IList;
            if (type.IsArray || list != null)
            {
                if (list == null)
                {
                    list = (System.Collections.IList)value;
                }

                var allNumbers = list.Count > 0;
                for (var i = 0; i < list.Count; i++)
                {
                    if (!IsNumeric(list[i]))
                    {
                        allNumbers = false;
                        break;
                    }
                }

                if (allNumbers)
                {
                    sb.Append("{\"type\":\"series\",\"values\":[");
                    for (var i = 0; i < list.Count; i++)
                    {
                        if (i > 0)
                        {
                            sb.Append(',');
                        }

                        sb.Append(Convert.ToDouble(list[i], CultureInfo.InvariantCulture)
                            .ToString("G17", CultureInfo.InvariantCulture));
                    }

                    sb.Append("]}");
                    return;
                }

                sb.Append("{\"type\":\"string\",\"value\":")
                    .Append(Quote(list.Count + " items"))
                    .Append('}');
                return;
            }

            if (depth < 3 && (type.IsClass || (type.IsValueType && !type.IsPrimitive)))
            {
                sb.Append("{\"type\":\"object\",\"fields\":");
                sb.Append(SerializePlainObjectFields(value, depth + 1));
                sb.Append('}');
                return;
            }

            sb.Append("{\"type\":\"string\",\"value\":")
                .Append(Quote(value.ToString()))
                .Append('}');
        }

        static string SerializePlainObjectFields(object target, int depth)
        {
            var sb = new StringBuilder();
            sb.Append('{');
            var type = target.GetType();
            var fields = type.GetFields(
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
            var first = true;
            foreach (var field in fields)
            {
                if (field.IsNotSerialized)
                {
                    continue;
                }

                if (!field.IsPublic && field.GetCustomAttribute<SerializeField>() == null)
                {
                    continue;
                }

                if (!first)
                {
                    sb.Append(',');
                }

                first = false;
                sb.Append(Quote(field.Name)).Append(':');
                AppendValue(sb, field.GetValue(target), depth);
            }

            sb.Append('}');
            return sb.ToString();
        }

        static bool IsNumeric(object value)
        {
            if (value == null || value is bool)
            {
                return false;
            }

            switch (Type.GetTypeCode(value.GetType()))
            {
                case TypeCode.Byte:
                case TypeCode.SByte:
                case TypeCode.Int16:
                case TypeCode.UInt16:
                case TypeCode.Int32:
                case TypeCode.UInt32:
                case TypeCode.Int64:
                case TypeCode.UInt64:
                case TypeCode.Single:
                case TypeCode.Double:
                case TypeCode.Decimal:
                    return true;
                default:
                    return false;
            }
        }

        static void AppendJsonString(
            StringBuilder sb,
            string indent,
            string key,
            string value,
            bool trailingComma)
        {
            sb.Append(indent).Append(Quote(key)).Append(": ");
            if (value == null)
            {
                sb.Append("null");
            }
            else
            {
                sb.Append(Quote(value));
            }

            if (trailingComma)
            {
                sb.Append(',');
            }

            sb.Append('\n');
        }

        static string Quote(string value)
        {
            if (value == null)
            {
                return "null";
            }

            var escaped = value
                .Replace("\\", "\\\\")
                .Replace("\"", "\\\"")
                .Replace("\n", "\\n")
                .Replace("\r", "\\r")
                .Replace("\t", "\\t");
            return "\"" + escaped + "\"";
        }
    }
}
#endif
