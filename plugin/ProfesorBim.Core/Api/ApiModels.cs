using ProfesorBim.Core.Model;

namespace ProfesorBim.Core.Api;

// DTOs de contracts/openapi.yaml. Nombres en PascalCase → snake_case vía ProfesorBimJsonContext.

public sealed class IssueCreate
{
    public string? ElementGuid { get; set; }
    public string RuleId { get; set; } = "";
    public string Severity { get; set; } = "";
    public string Message { get; set; } = "";
    public string? RelatedGuid { get; set; }

    public static IssueCreate From(ValidationIssue i) => new()
    {
        ElementGuid = i.ElementGuid,
        RuleId = i.RuleId,
        Severity = i.Severity,
        Message = i.Message,
        RelatedGuid = i.RelatedGuid,
    };
}

public sealed class Issue
{
    public int Id { get; set; }
    public int SnapshotId { get; set; }
    public string? ElementGuid { get; set; }
    public string RuleId { get; set; } = "";
    public string Severity { get; set; } = "";
    public string Message { get; set; } = "";
    public string? RelatedGuid { get; set; }
    public string Status { get; set; } = "";
    public string? Discipline { get; set; }
    public string? FirstSeenAt { get; set; }
    public string? ResolvedAt { get; set; }
    public string? FixedBy { get; set; }
}

public sealed class IssueUpdate
{
    public string Status { get; set; } = IssueStatuses.Fixed;
    public string? FixedBy { get; set; }
}

public static class IssueStatuses
{
    public const string Open = "open";
    public const string Fixed = "fixed";
    public const string Dismissed = "dismissed";
}

public static class CdeStates
{
    public const string Wip = "WIP";
    public const string Shared = "SHARED";
    public const string Published = "PUBLISHED";

    /// <summary>Estados elegibles desde el plugin (ARCHIVED lo mueve BIM).</summary>
    public static readonly IReadOnlyList<string> Selectable = [Wip, Shared, Published];
}

public sealed class SnapshotCreate
{
    public string ProjectCode { get; set; } = "HKT";
    public string FileName { get; set; } = "";
    public string VersionLabel { get; set; } = "";
    public string CdeState { get; set; } = CdeStates.Wip;
    public string RulesVersion { get; set; } = "";
    public string? Author { get; set; }
    public List<ElementData> Elements { get; set; } = new();
    public List<IssueCreate> Issues { get; set; } = new();
}

public sealed class Snapshot
{
    public int Id { get; set; }
    public string ProjectCode { get; set; } = "";
    public string FileName { get; set; } = "";
    public string VersionLabel { get; set; } = "";
    public string CdeState { get; set; } = "";
    public string RulesVersion { get; set; } = "";
    public string? Author { get; set; }
    public string? CreatedAt { get; set; }
    public int ElementCount { get; set; }
    public int OpenIssueCount { get; set; }
}

public sealed class FeedbackCreate
{
    public string ElementGuid { get; set; } = "";
    public string RuleId { get; set; } = "";
    public int? IssueId { get; set; }
    public string Reason { get; set; } = FeedbackReasons.Otro;
    public string? Comment { get; set; }
    public string? Author { get; set; }
}

public sealed class Feedback
{
    public int Id { get; set; }
    public string ElementGuid { get; set; } = "";
    public string RuleId { get; set; } = "";
    public string Reason { get; set; } = "";
    public string? CreatedAt { get; set; }
}

/// <summary>Enum FeedbackReason de openapi con etiquetas en español.</summary>
public static class FeedbackReasons
{
    public const string NoEntiendoRegla = "no_entiendo_regla";
    public const string NoEncuentroCodigo = "no_encuentro_codigo";
    public const string FaltaInformacion = "falta_informacion";
    public const string ReglaNoAplica = "regla_no_aplica";
    public const string ErrorDelPlugin = "error_del_plugin";
    public const string Otro = "otro";

    public static readonly IReadOnlyList<KeyValuePair<string, string>> All =
    [
        new(NoEntiendoRegla, "No entiendo la regla"),
        new(NoEncuentroCodigo, "No encuentro el código correcto"),
        new(FaltaInformacion, "Me falta información del proyecto"),
        new(ReglaNoAplica, "La regla no aplica a este elemento"),
        new(ErrorDelPlugin, "Error del plugin"),
        new(Otro, "Otro"),
    ];
}

public sealed class ExplainRequest
{
    public string RuleId { get; set; } = "";
    public ElementData? Element { get; set; }
}

public sealed class Explanation
{
    public string RuleId { get; set; } = "";
    public string Text { get; set; } = "";
    public bool Cached { get; set; }
    public string Mode { get; set; } = "";
}

public sealed class SuggestClassificationRequest
{
    public ElementData Element { get; set; } = new();
}

public sealed class UniclassCodeDto
{
    public string Code { get; set; } = "";
    public string TitleEs { get; set; } = "";
    public string? TitleEn { get; set; }
    public string Table { get; set; } = "";
    public List<string> RevitCategories { get; set; } = new();
}

public sealed class ClassificationSuggestion
{
    public string ElementGuid { get; set; } = "";
    public List<UniclassCodeDto> Candidates { get; set; } = new();
    public string? SuggestedCode { get; set; }
    public string? Reason { get; set; }
    public string Mode { get; set; } = "";
}

public sealed class HealthResponse
{
    public string Status { get; set; } = "";
    public string Version { get; set; } = "";
    public string LlmMode { get; set; } = "";
}

public sealed class ErrorResponse
{
    public string? Detail { get; set; }
}
