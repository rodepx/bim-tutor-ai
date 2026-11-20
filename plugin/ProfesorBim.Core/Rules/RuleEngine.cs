using System.Collections.Concurrent;
using System.Text.RegularExpressions;
using ProfesorBim.Core.Model;

namespace ProfesorBim.Core.Rules;

/// <summary>
/// Motor de reglas puro (sin Revit). Evalúa solo reglas con enabled = true.
/// La detección geométrica de no_overlap se hace en la capa Revit y llega como <see cref="OverlapPair"/>.
/// </summary>
public sealed class RuleEngine
{
    private static readonly TimeSpan RegexTimeout = TimeSpan.FromMilliseconds(200);
    private readonly ConcurrentDictionary<string, Regex> _regexCache = new(StringComparer.Ordinal);

    public RuleEngine(RuleSet rules, UniclassTable uniclass)
    {
        Rules = rules;
        Uniclass = uniclass;
    }

    public RuleSet Rules { get; }

    public UniclassTable Uniclass { get; }

    /// <summary>Valida elementos (reglas de nivel element). Los pares de superposición son opcionales.</summary>
    public List<ValidationIssue> ValidateElements(IEnumerable<ElementData> elements, IEnumerable<OverlapPair>? overlaps = null)
    {
        var issues = new List<ValidationIssue>();
        var elementRules = Rules.EnabledRules.Where(r => r.Scope.Level != "document").ToList();
        var byGuid = new Dictionary<string, ElementData>(StringComparer.Ordinal);

        foreach (var element in elements)
        {
            byGuid[element.Guid] = element;
            foreach (var rule in elementRules)
            {
                if (rule.Check == RuleChecks.NoOverlap || !rule.AppliesToCategory(element.Category))
                {
                    continue;
                }
                EvaluateElement(rule, element, issues);
            }
        }

        if (overlaps is not null)
        {
            var pairs = overlaps.ToList();
            foreach (var rule in elementRules.Where(r => r.Check == RuleChecks.NoOverlap))
            {
                EvaluateOverlaps(rule, pairs, byGuid, issues);
            }
        }

        return issues;
    }

    /// <summary>
    /// Solo reglas no_overlap. <paramref name="known"/> aporta datos de los elementos (categoría, tipo) para el mensaje;
    /// los pares cuyo elemento no esté en <paramref name="known"/> se reportan igual.
    /// </summary>
    public List<ValidationIssue> ValidateOverlaps(IEnumerable<ElementData> known, IEnumerable<OverlapPair> overlaps)
    {
        var issues = new List<ValidationIssue>();
        var byGuid = new Dictionary<string, ElementData>(StringComparer.Ordinal);
        foreach (var e in known)
        {
            byGuid[e.Guid] = e;
        }
        var pairs = overlaps.ToList();
        foreach (var rule in Rules.EnabledRules.Where(r => r.Check == RuleChecks.NoOverlap && r.Scope.Level != "document"))
        {
            EvaluateOverlaps(rule, pairs, byGuid, issues);
        }
        return issues;
    }

    /// <summary>Valida reglas de nivel documento (file_naming). <paramref name="fileName"/> sin extensión.</summary>
    public List<ValidationIssue> ValidateDocument(string fileName)
    {
        var issues = new List<ValidationIssue>();
        foreach (var rule in Rules.EnabledRules.Where(r => r.Scope.Level == "document"))
        {
            if (rule.Check == RuleChecks.FileNaming)
            {
                var pattern = rule.GetString("pattern");
                var name = StripExtension(fileName);
                if (pattern is not null && !GetRegex(pattern, RegexOptions.None).IsMatch(name))
                {
                    issues.Add(new ValidationIssue
                    {
                        Rule = rule,
                        Message = Format(rule.Message, fileName: name),
                    });
                }
            }
        }
        return issues;
    }

    private void EvaluateElement(Rule rule, ElementData e, List<ValidationIssue> issues)
    {
        switch (rule.Check)
        {
            case RuleChecks.TypeNameNotGeneric:
            {
                var patterns = rule.GetStringArray("forbidden_patterns");
                if (patterns.Any(p => GetRegex(p, RegexOptions.IgnoreCase).IsMatch(e.TypeName ?? "")))
                {
                    issues.Add(Make(rule, e));
                }
                break;
            }
            case RuleChecks.TypeNamePattern:
            {
                var pattern = rule.GetPatternForCategory(e.Category);
                if (pattern is not null && !GetRegex(pattern, RegexOptions.None).IsMatch(e.TypeName ?? ""))
                {
                    issues.Add(Make(rule, e));
                }
                break;
            }
            case RuleChecks.ClassificationRequired:
            {
                if (string.IsNullOrWhiteSpace(e.ClassificationCode))
                {
                    issues.Add(Make(rule, e, parameter: Rules.Classification.ParameterName));
                }
                break;
            }
            case RuleChecks.ClassificationExists:
            {
                // Vacío lo reporta classification_required.
                if (!string.IsNullOrWhiteSpace(e.ClassificationCode) && !Uniclass.IsValidFor(e.ClassificationCode, e.Category))
                {
                    issues.Add(Make(rule, e, parameter: e.ClassificationParameterFound ?? Rules.Classification.ParameterName));
                }
                break;
            }
            case RuleChecks.RequiredParameters:
            {
                foreach (var p in rule.GetParametersByCategory(e.Category))
                {
                    if (!e.Parameters.TryGetValue(p, out var value) || string.IsNullOrWhiteSpace(value))
                    {
                        issues.Add(Make(rule, e, parameter: p));
                    }
                }
                break;
            }
            case RuleChecks.LevelRequired:
            {
                if (string.IsNullOrWhiteSpace(e.Level))
                {
                    issues.Add(Make(rule, e));
                }
                break;
            }
        }
    }

    private void EvaluateOverlaps(Rule rule, List<OverlapPair> pairs, Dictionary<string, ElementData> byGuid, List<ValidationIssue> issues)
    {
        var catA = rule.GetString("category_a");
        var catB = rule.GetString("category_b");
        var ignoreIfJoined = rule.GetBool("ignore_if_joined", true);
        var seen = new HashSet<(string, string)>();

        foreach (var pair in pairs)
        {
            if (ignoreIfJoined && pair.AreJoined)
            {
                continue;
            }
            if (!seen.Add((pair.GuidA, pair.GuidB)))
            {
                continue;
            }
            // El issue se asigna al elemento de category_a (un issue por par, no se duplica).
            byGuid.TryGetValue(pair.GuidA, out var a);
            byGuid.TryGetValue(pair.GuidB, out var b);
            if (a is not null && catA is not null && a.Category != catA)
            {
                continue;
            }
            if (b is not null && catB is not null && b.Category != catB)
            {
                continue;
            }
            issues.Add(new ValidationIssue
            {
                Rule = rule,
                ElementGuid = pair.GuidA,
                ElementId = a?.ElementId,
                Category = a?.Category ?? catA,
                TypeName = a?.TypeName,
                RelatedGuid = pair.GuidB,
                Element = a,
                Message = Format(rule.Message, a, otherGuid: pair.GuidB),
            });
        }
    }

    private ValidationIssue Make(Rule rule, ElementData e, string? parameter = null) => new()
    {
        Rule = rule,
        ElementGuid = e.Guid,
        ElementId = e.ElementId,
        Category = e.Category,
        TypeName = e.TypeName,
        Parameter = parameter,
        Element = e,
        Message = Format(rule.Message, e, parameter: parameter),
    };

    /// <summary>Reemplaza placeholders {type_name} {category} {code} {parameter} {other_guid} {file_name}.</summary>
    public static string Format(string template, ElementData? e = null, string? parameter = null, string? otherGuid = null, string? fileName = null) =>
        template
            .Replace("{type_name}", e?.TypeName ?? "", StringComparison.Ordinal)
            .Replace("{category}", e?.Category ?? "", StringComparison.Ordinal)
            .Replace("{code}", e?.ClassificationCode ?? "", StringComparison.Ordinal)
            .Replace("{parameter}", parameter ?? "", StringComparison.Ordinal)
            .Replace("{other_guid}", otherGuid ?? "", StringComparison.Ordinal)
            .Replace("{file_name}", fileName ?? "", StringComparison.Ordinal);

    public static string StripExtension(string fileName) =>
        fileName.EndsWith(".rvt", StringComparison.OrdinalIgnoreCase) || fileName.EndsWith(".rfa", StringComparison.OrdinalIgnoreCase)
            ? fileName[..^4]
            : fileName;

    private Regex GetRegex(string pattern, RegexOptions options) =>
        _regexCache.GetOrAdd($"{(int)options}:{pattern}", _ => new Regex(pattern, options | RegexOptions.CultureInvariant, RegexTimeout));
}
