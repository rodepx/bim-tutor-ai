using ProfesorBim.Core.Rules;

namespace ProfesorBim.Core.Model;

/// <summary>Incumplimiento detectado por el motor de reglas.</summary>
public sealed class ValidationIssue
{
    public required Rule Rule { get; init; }

    public string RuleId => Rule.Id;

    public string Severity => Rule.Severity;

    public required string Message { get; init; }

    /// <summary>UniqueId del elemento; null para reglas de documento.</summary>
    public string? ElementGuid { get; init; }

    public long? ElementId { get; init; }

    public string? Category { get; init; }

    public string? TypeName { get; init; }

    /// <summary>Otro elemento implicado (no_overlap).</summary>
    public string? RelatedGuid { get; init; }

    /// <summary>Parámetro concreto implicado (required_parameters / clasificación).</summary>
    public string? Parameter { get; init; }

    /// <summary>Snapshot del elemento cuando se detectó (para IA y fixes).</summary>
    public ElementData? Element { get; init; }

    /// <summary>Clave estable para comparar issues entre validaciones.</summary>
    public string Key => $"{ElementGuid ?? "DOC"}|{RuleId}|{Parameter ?? ""}|{RelatedGuid ?? ""}";
}
