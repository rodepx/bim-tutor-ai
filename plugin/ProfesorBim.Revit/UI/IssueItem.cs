using System.Windows.Media;
using ProfesorBim.Core.Model;
using ProfesorBim.Core.Rules;

namespace ProfesorBim.Revit.UI;

/// <summary>Fila del panel (solo lectura; se reconstruye en cada validación).</summary>
public sealed class IssueItem
{
    private static readonly Brush ErrorBrush = Frozen(Color.FromRgb(0xD3, 0x2F, 0x2F));
    private static readonly Brush WarningBrush = Frozen(Color.FromRgb(0xF5, 0x9E, 0x0B));
    private static readonly Brush InfoBrush = Frozen(Color.FromRgb(0x1E, 0x6F, 0xB8));

    public IssueItem(ValidationIssue issue) => Issue = issue;

    public ValidationIssue Issue { get; }

    public string Key => Issue.Key;

    public int SeverityRank => Severities.Rank(Issue.Severity);

    public string SeverityLabel => Severities.LabelEs(Issue.Severity);

    public Brush SeverityBrush => Issue.Severity switch
    {
        Severities.Error => ErrorBrush,
        Severities.Warning => WarningBrush,
        _ => InfoBrush,
    };

    public string Title => $"{Issue.RuleId} · {Issue.Rule.Name}";

    public string Message => Issue.Message;

    public string Subtitle => Issue.ElementGuid is null
        ? "Documento"
        : $"{Issue.Category} · {Issue.TypeName} · Id {Issue.ElementId}";

    private static Brush Frozen(Color c)
    {
        var b = new SolidColorBrush(c);
        b.Freeze();
        return b;
    }
}
