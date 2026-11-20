using System.Globalization;
using System.Text.RegularExpressions;
using ProfesorBim.Core.Model;
using ProfesorBim.Core.Rules;

namespace ProfesorBim.Core.Api;

public static class SnapshotFactory
{
    private static readonly Regex ProjectCodeRegex = new("^[A-Z0-9]{2,6}$", RegexOptions.CultureInvariant);

    /// <summary>Primer segmento del nombre de archivo (antes de '-') si parece código de proyecto; si no, "HKT".</summary>
    public static string ProjectCodeFrom(string fileName)
    {
        var first = RuleEngine.StripExtension(fileName).Split('-')[0].Trim();
        return ProjectCodeRegex.IsMatch(first) ? first : "HKT";
    }

    public static string VersionLabel(DateTime localNow) => localNow.ToString("yyyyMMdd-HHmm", CultureInfo.InvariantCulture);

    public static SnapshotCreate Create(
        string fileName,
        string cdeState,
        string rulesVersion,
        string? author,
        IEnumerable<ElementData> elements,
        IEnumerable<ValidationIssue> issues,
        DateTime localNow)
    {
        var name = RuleEngine.StripExtension(fileName);
        return new SnapshotCreate
        {
            ProjectCode = ProjectCodeFrom(name),
            FileName = name,
            VersionLabel = VersionLabel(localNow),
            CdeState = cdeState,
            RulesVersion = rulesVersion,
            Author = string.IsNullOrWhiteSpace(author) ? null : author,
            Elements = elements.ToList(),
            Issues = issues.Select(IssueCreate.From).ToList(),
        };
    }
}
