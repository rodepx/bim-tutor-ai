using System.Text.Json;

namespace ProfesorBim.Core.Rules;

/// <summary>Espejo de contracts/rules.schema.json (data/rules.json).</summary>
public sealed class RuleSet
{
    public string Version { get; set; } = "0.0.0";
    public ClassificationConfig Classification { get; set; } = new();
    public Dictionary<string, List<string>> Disciplines { get; set; } = new();
    public List<Rule> Rules { get; set; } = new();

    public IEnumerable<Rule> EnabledRules => Rules.Where(r => r.Enabled);

    /// <summary>Disciplina (ARQ/EST/MEP) de una categoría OST_*, o null si no está mapeada.</summary>
    public string? DisciplineOf(string category)
    {
        foreach (var (discipline, categories) in Disciplines)
        {
            if (categories.Contains(category, StringComparer.Ordinal))
            {
                return discipline;
            }
        }
        return null;
    }

    /// <summary>Todas las categorías mencionadas en disciplinas y en el scope de las reglas activas.</summary>
    public IReadOnlyCollection<string> AllCategories()
    {
        var set = new HashSet<string>(StringComparer.Ordinal);
        foreach (var cats in Disciplines.Values)
        {
            set.UnionWith(cats);
        }
        foreach (var rule in EnabledRules)
        {
            if (rule.Scope.Categories is { } c)
            {
                set.UnionWith(c);
            }
        }
        return set;
    }

    /// <summary>Nombres de parámetro de clasificación en orden de prioridad.</summary>
    public IReadOnlyList<string> ClassificationParameterNames()
    {
        var list = new List<string> { Classification.ParameterName };
        list.AddRange(Classification.FallbackParameterNames);
        return list;
    }

    /// <summary>Parámetros LOIN exigidos para una categoría (unión de todas las reglas required_parameters activas).</summary>
    public IReadOnlyList<string> RequiredParametersFor(string category)
    {
        var result = new List<string>();
        foreach (var rule in EnabledRules.Where(r => r.Check == RuleChecks.RequiredParameters))
        {
            foreach (var p in rule.GetParametersByCategory(category))
            {
                if (!result.Contains(p, StringComparer.Ordinal))
                {
                    result.Add(p);
                }
            }
        }
        return result;
    }
}

public sealed class ClassificationConfig
{
    public string ParameterName { get; set; } = "Uniclass_Codigo";
    public List<string> FallbackParameterNames { get; set; } = new();
    public string TableFile { get; set; } = "data/uniclass_subset.csv";
}

public sealed class Rule
{
    public string Id { get; set; } = "";
    public string Name { get; set; } = "";
    public string Check { get; set; } = "";
    public string Severity { get; set; } = "warning";
    public RuleScope Scope { get; set; } = new();
    public JsonElement Params { get; set; }
    public string Message { get; set; } = "";
    public string Explanation { get; set; } = "";
    public RuleFix Fix { get; set; } = new();
    public string BepRef { get; set; } = "";
    public bool Enabled { get; set; }

    public bool AppliesToCategory(string category) =>
        Scope.Categories is null || Scope.Categories.Count == 0 || Scope.Categories.Contains(category, StringComparer.Ordinal);

    public string? GetString(string name) =>
        Params.ValueKind == JsonValueKind.Object && Params.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String
            ? v.GetString()
            : null;

    public bool GetBool(string name, bool defaultValue) =>
        Params.ValueKind == JsonValueKind.Object && Params.TryGetProperty(name, out var v) && v.ValueKind is JsonValueKind.True or JsonValueKind.False
            ? v.GetBoolean()
            : defaultValue;

    public IReadOnlyList<string> GetStringArray(string name)
    {
        if (Params.ValueKind != JsonValueKind.Object || !Params.TryGetProperty(name, out var v) || v.ValueKind != JsonValueKind.Array)
        {
            return Array.Empty<string>();
        }
        return v.EnumerateArray().Where(x => x.ValueKind == JsonValueKind.String).Select(x => x.GetString()!).ToList();
    }

    /// <summary>params.patterns_by_category[category] (type_name_pattern).</summary>
    public string? GetPatternForCategory(string category)
    {
        if (Params.ValueKind == JsonValueKind.Object
            && Params.TryGetProperty("patterns_by_category", out var map)
            && map.ValueKind == JsonValueKind.Object
            && map.TryGetProperty(category, out var p)
            && p.ValueKind == JsonValueKind.String)
        {
            return p.GetString();
        }
        return null;
    }

    /// <summary>params.parameters_by_category[category] (required_parameters).</summary>
    public IReadOnlyList<string> GetParametersByCategory(string category)
    {
        if (Params.ValueKind == JsonValueKind.Object
            && Params.TryGetProperty("parameters_by_category", out var map)
            && map.ValueKind == JsonValueKind.Object
            && map.TryGetProperty(category, out var arr)
            && arr.ValueKind == JsonValueKind.Array)
        {
            return arr.EnumerateArray().Where(x => x.ValueKind == JsonValueKind.String).Select(x => x.GetString()!).ToList();
        }
        return Array.Empty<string>();
    }
}

public sealed class RuleScope
{
    public string Level { get; set; } = "element";
    public List<string>? Categories { get; set; }
}

public sealed class RuleFix
{
    public string Type { get; set; } = FixTypes.None;
    public string? Parameter { get; set; }
    public string? ValueSource { get; set; }
    public string? Label { get; set; }
}

public static class RuleChecks
{
    public const string TypeNameNotGeneric = "type_name_not_generic";
    public const string TypeNamePattern = "type_name_pattern";
    public const string ClassificationRequired = "classification_required";
    public const string ClassificationExists = "classification_exists";
    public const string NoOverlap = "no_overlap";
    public const string RequiredParameters = "required_parameters";
    public const string LevelRequired = "level_required";
    public const string FileNaming = "file_naming";
}

public static class FixTypes
{
    public const string None = "none";
    public const string SetParameter = "set_parameter";
    public const string RenameType = "rename_type";
    public const string JoinGeometry = "join_geometry";
}

public static class ValueSources
{
    public const string UserInput = "user_input";
    public const string AiSuggestion = "ai_suggestion";
    public const string PickList = "pick_list";
}

public static class Severities
{
    public const string Error = "error";
    public const string Warning = "warning";
    public const string Info = "info";

    public static int Rank(string severity) => severity switch
    {
        Error => 0,
        Warning => 1,
        _ => 2,
    };

    public static string LabelEs(string severity) => severity switch
    {
        Error => "Errores",
        Warning => "Advertencias",
        _ => "Información",
    };
}
