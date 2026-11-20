using System.Text.Json.Serialization;

namespace ProfesorBim.Core.Model;

/// <summary>
/// Elemento leído del modelo. Se serializa como el schema <c>Element</c> de contracts/openapi.yaml (snake_case).
/// Las propiedades marcadas JsonIgnore son solo para el motor/UI del plugin.
/// </summary>
public sealed class ElementData
{
    /// <summary>UniqueId de Revit.</summary>
    public string Guid { get; set; } = "";

    public long? ElementId { get; set; }

    /// <summary>Nombre de BuiltInCategory, p. ej. OST_Walls.</summary>
    public string Category { get; set; } = "";

    /// <summary>ARQ / EST / MEP.</summary>
    public string? Discipline { get; set; }

    public string? FamilyName { get; set; }

    public string TypeName { get; set; } = "";

    public string? ClassificationCode { get; set; }

    public string? Level { get; set; }

    public double? VolumeM3 { get; set; }

    public double? AreaM2 { get; set; }

    public double? LengthM { get; set; }

    /// <summary>Parámetros LOIN (nombre → valor como texto, null si falta o está vacío).</summary>
    public Dictionary<string, string?> Parameters { get; set; } = new();

    /// <summary>ElementId del tipo (para renombrar). No se envía.</summary>
    [JsonIgnore]
    public long? TypeElementId { get; set; }

    /// <summary>Parámetro donde se encontró el código de clasificación (si se encontró). No se envía.</summary>
    [JsonIgnore]
    public string? ClassificationParameterFound { get; set; }
}

/// <summary>Par de elementos cuya geometría se intersecta (calculado en la capa Revit).</summary>
/// <param name="GuidA">Elemento de category_a.</param>
/// <param name="GuidB">Elemento de category_b.</param>
/// <param name="AreJoined">true si ya tienen unión de geometría.</param>
public sealed record OverlapPair(string GuidA, string GuidB, bool AreJoined);
