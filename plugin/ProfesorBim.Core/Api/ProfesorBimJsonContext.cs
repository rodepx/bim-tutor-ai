using System.Text.Json.Serialization;
using ProfesorBim.Core.Config;
using ProfesorBim.Core.Model;
using ProfesorBim.Core.Rules;

namespace ProfesorBim.Core.Api;

/// <summary>System.Text.Json con generación de código; snake_case exacto como openapi.yaml.</summary>
[JsonSourceGenerationOptions(
    PropertyNamingPolicy = JsonKnownNamingPolicy.SnakeCaseLower,
    PropertyNameCaseInsensitive = true,
    ReadCommentHandling = System.Text.Json.JsonCommentHandling.Skip,
    AllowTrailingCommas = true,
    WriteIndented = false)]
[JsonSerializable(typeof(RuleSet))]
[JsonSerializable(typeof(PluginSettings))]
[JsonSerializable(typeof(ElementData))]
[JsonSerializable(typeof(SnapshotCreate))]
[JsonSerializable(typeof(Snapshot))]
[JsonSerializable(typeof(List<Issue>))]
[JsonSerializable(typeof(Issue))]
[JsonSerializable(typeof(IssueUpdate))]
[JsonSerializable(typeof(FeedbackCreate))]
[JsonSerializable(typeof(Feedback))]
[JsonSerializable(typeof(ExplainRequest))]
[JsonSerializable(typeof(Explanation))]
[JsonSerializable(typeof(SuggestClassificationRequest))]
[JsonSerializable(typeof(ClassificationSuggestion))]
[JsonSerializable(typeof(HealthResponse))]
[JsonSerializable(typeof(ErrorResponse))]
public sealed partial class ProfesorBimJsonContext : JsonSerializerContext
{
}
