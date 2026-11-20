using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using ProfesorBim.Core.Api;
using ProfesorBim.Core.Model;
using ProfesorBim.Core.Rules;
using ProfesorBim.Revit.Model;

namespace ProfesorBim.Revit.UI;

/// <summary>
/// Panel acoplable no modal. Corre en el hilo de UI de Revit, pero FUERA del contexto de la API:
/// todo acceso al modelo pasa por <see cref="Infrastructure.RevitTaskQueue"/> (ExternalEvent) y todo HTTP es async.
/// </summary>
public partial class IssuesPanel : UserControl
{
    private readonly App _app;
    private bool _suppressSelection;
    private bool _busy;

    public IssuesPanel(App app)
    {
        _app = app;
        InitializeComponent();
        CdeCombo.ItemsSource = CdeStates.Selectable;
        CdeCombo.SelectedItem = app.SelectedCdeState;
        SummaryText.Text = "Abre un modelo y pulsa «Validar todo».";
    }

    private IssueItem? Selected => IssueList.SelectedItem as IssueItem;

    // ---------- Llamadas desde otros hilos / Revit ----------

    public void SetStatus(string text)
    {
        if (!Dispatcher.CheckAccess())
        {
            Dispatcher.BeginInvoke(new Action(() => SetStatus(text)));
            return;
        }
        StatusText.Text = $"[{DateTime.Now:HH:mm:ss}] {text}";
    }

    public void RefreshIssues()
    {
        if (!Dispatcher.CheckAccess())
        {
            Dispatcher.BeginInvoke(new Action(RefreshIssues));
            return;
        }

        var selectedKey = Selected?.Key;
        var items = _app.Session.Issues.Select(i => new IssueItem(i)).ToList();
        var view = new ListCollectionView(items);
        view.GroupDescriptions.Add(new PropertyGroupDescription(nameof(IssueItem.SeverityLabel)));
        view.SortDescriptions.Add(new SortDescription(nameof(IssueItem.SeverityRank), ListSortDirection.Ascending));
        view.SortDescriptions.Add(new SortDescription(nameof(IssueItem.Title), ListSortDirection.Ascending));

        _suppressSelection = true;
        try
        {
            IssueList.ItemsSource = view;
            var again = selectedKey is null ? null : items.FirstOrDefault(i => i.Key == selectedKey);
            IssueList.SelectedItem = again;
            ShowDetail(again);
        }
        finally
        {
            _suppressSelection = false;
        }

        var errors = items.Count(i => i.Issue.Severity == Severities.Error);
        var warnings = items.Count(i => i.Issue.Severity == Severities.Warning);
        var file = string.IsNullOrEmpty(_app.Session.FileName) ? "(sin documento)" : _app.Session.FileName;
        SummaryText.Text = $"{file} — {_app.Session.Elements.Count} elementos · {errors} errores · {warnings} advertencias" +
                           (errors == 0 ? " · listo para SHARED" : "");
    }

    // ---------- Barra superior ----------

    private async void OnValidateAll(object sender, RoutedEventArgs e)
    {
        await RunGuarded(async () =>
        {
            SetStatus("Validando todo el modelo…");
            var count = await _app.Queue.RunAsync(app =>
            {
                var doc = RequireDocument(app);
                _app.Live.Reset();
                _app.Session.ValidateAll(doc);
                return _app.Session.Issues.Count;
            });
            SetStatus($"Validación completa: {count} issues.");
        });
    }

    private async void OnSend(object sender, RoutedEventArgs e)
    {
        await RunGuarded(async () =>
        {
            var cde = _app.SelectedCdeState;
            // Recolección en el hilo de Revit; envío en segundo plano.
            var snapshot = await _app.Queue.RunAsync(app =>
            {
                var doc = RequireDocument(app);
                _app.Live.Reset();
                _app.Session.ValidateAll(doc);
                return _app.Session.BuildSnapshot(cde);
            });
            _ = _app.Sync.SendSnapshotAsync(snapshot);
        });
    }

    private void OnCdeChanged(object sender, SelectionChangedEventArgs e)
    {
        if (CdeCombo.SelectedItem is string s)
        {
            _app.SelectedCdeState = s;
        }
    }

    // ---------- Lista / detalle ----------

    private async void OnIssueSelected(object sender, SelectionChangedEventArgs e)
    {
        ShowDetail(Selected);
        if (_suppressSelection || Selected is null || Selected.Issue.ElementId is null)
        {
            return;
        }
        await ZoomTo(Selected.Issue);
    }

    private void ShowDetail(IssueItem? item)
    {
        if (item is null)
        {
            DetailPanel.Visibility = System.Windows.Visibility.Collapsed;
            return;
        }
        var issue = item.Issue;
        var rule = issue.Rule;
        DetailPanel.Visibility = System.Windows.Visibility.Visible;
        DetailTitle.Text = $"{rule.Id} — {rule.Name} (BEP {rule.BepRef})";
        DetailMessage.Text = issue.Message;
        DetailExplanation.Text = rule.Explanation;
        DetailAi.Visibility = System.Windows.Visibility.Collapsed;
        DetailAi.Text = "";

        var hasFix = rule.Fix.Type != FixTypes.None && (issue.ElementId is not null);
        FixButton.Visibility = hasFix ? System.Windows.Visibility.Visible : System.Windows.Visibility.Collapsed;
        FixButton.Content = string.IsNullOrWhiteSpace(rule.Fix.Label) ? "Corregir" : rule.Fix.Label;
        DetailFixHint.Visibility = hasFix ? System.Windows.Visibility.Collapsed : System.Windows.Visibility.Visible;
        DetailFixHint.Text = "Corrección manual: " + (rule.Fix.Label ?? "ver explicación");
        ZoomButton.Visibility = issue.ElementId is null ? System.Windows.Visibility.Collapsed : System.Windows.Visibility.Visible;
    }

    private async void OnZoom(object sender, RoutedEventArgs e)
    {
        if (Selected is { } item)
        {
            await ZoomTo(item.Issue);
        }
    }

    private async Task ZoomTo(ValidationIssue issue)
    {
        try
        {
            await _app.Queue.RunAsync(app =>
            {
                var uidoc = app.ActiveUIDocument ?? throw new InvalidOperationException("No hay documento activo.");
                var doc = uidoc.Document;
                var ids = new List<ElementId>();
                if (issue.ElementId is long id && doc.GetElement(new ElementId(id)) is not null)
                {
                    ids.Add(new ElementId(id));
                }
                if (issue.RelatedGuid is not null && doc.GetElement(issue.RelatedGuid) is { } other)
                {
                    ids.Add(other.Id);
                }
                if (ids.Count == 0)
                {
                    return;
                }
                uidoc.Selection.SetElementIds(ids);
                uidoc.ShowElements(ids);
            });
        }
        catch (Exception ex)
        {
            SetStatus("No se pudo mostrar el elemento: " + ex.Message);
        }
    }

    private async void OnExplain(object sender, RoutedEventArgs e)
    {
        if (Selected is not { } item)
        {
            return;
        }
        var issue = item.Issue;
        DetailAi.Visibility = System.Windows.Visibility.Visible;
        DetailAi.Text = "Consultando a la IA…";
        ExplainButton.IsEnabled = false;
        try
        {
            var result = await _app.Backend.ExplainAsync(issue.RuleId, issue.Element);
            if (Selected?.Key != item.Key)
            {
                return;
            }
            DetailAi.Text = result.Ok && result.Value is not null
                ? "IA: " + result.Value.Text
                : "IA no disponible: " + result.Error;
        }
        finally
        {
            ExplainButton.IsEnabled = true;
        }
    }

    // ---------- Corrección en 1 clic ----------

    private async void OnFix(object sender, RoutedEventArgs e)
    {
        if (Selected is not { } item || item.Issue.ElementId is not long elementId)
        {
            return;
        }
        var issue = item.Issue;
        var rule = issue.Rule;

        await RunGuarded(async () =>
        {
            Func<Document, FixResult>? op = null;
            switch (rule.Fix.Type)
            {
                case FixTypes.RenameType:
                {
                    if (issue.Element?.TypeElementId is not long typeId)
                    {
                        SetStatus("El elemento no tiene un tipo editable.");
                        return;
                    }
                    var name = Dialogs.AskText(this, rule.Fix.Label ?? "Renombrar tipo",
                        "Nuevo nombre de tipo (BEP §3: CAT_MATERIAL_DIMENSION, p. ej. MUR_CA_e25_FC210). Afecta a todas las instancias del tipo:",
                        issue.TypeName);
                    if (name is null)
                    {
                        return;
                    }
                    op = doc => FixService.RenameType(doc, typeId, name);
                    break;
                }
                case FixTypes.SetParameter:
                {
                    var parameter = rule.Fix.Parameter ?? issue.Parameter;
                    if (string.IsNullOrWhiteSpace(parameter))
                    {
                        SetStatus("La regla no indica qué parámetro corregir.");
                        return;
                    }
                    var value = await AskParameterValue(issue, rule, parameter);
                    if (value is null)
                    {
                        return;
                    }
                    var classificationNames = _app.Engine.Rules.ClassificationParameterNames();
                    var isClassification = classificationNames.Contains(parameter, StringComparer.Ordinal);
                    IReadOnlyList<string> names = isClassification
                        ? new[] { parameter }.Concat(classificationNames.Where(n => n != parameter)).ToList()
                        : [parameter];
                    op = doc => FixService.SetParameter(doc, elementId, names, value, preferType: isClassification);
                    break;
                }
                case FixTypes.JoinGeometry:
                {
                    if (issue.RelatedGuid is not { } other)
                    {
                        SetStatus("No se conoce el otro elemento de la superposición.");
                        return;
                    }
                    op = doc => FixService.JoinGeometry(doc, elementId, other);
                    break;
                }
            }
            if (op is null)
            {
                return;
            }

            SetStatus("Aplicando corrección…");
            var result = await _app.Queue.RunAsync(app =>
            {
                var doc = RequireDocument(app);
                var r = op(doc);
                if (r.Ok)
                {
                    // Revalida ya (cambios pendientes de DocumentChanged + elementos afectados).
                    _app.Live.Flush(doc, r.Affected);
                }
                return r;
            });
            SetStatus(result.Message);

            if (result.Ok && !_app.Session.HasIssueFor(issue.ElementGuid, issue.RuleId))
            {
                await _app.Sync.MarkFixedAsync(issue.ElementGuid, issue.RuleId);
            }
        });
    }

    private async Task<string?> AskParameterValue(ValidationIssue issue, Rule rule, string parameter)
    {
        var category = issue.Category ?? "";
        var title = rule.Fix.Label ?? "Completar parámetro";
        var current = issue.Element?.Parameters.GetValueOrDefault(parameter) ?? (parameter == _app.Engine.Rules.Classification.ParameterName ? issue.Element?.ClassificationCode : null);

        switch (rule.Fix.ValueSource)
        {
            case ValueSources.PickList:
                return Dialogs.Pick(this, title, $"Elige un código Uniclass válido para {category}:", PickItemsFor(category), current);

            case ValueSources.AiSuggestion:
            {
                if (issue.Element is null)
                {
                    return Dialogs.Pick(this, title, $"Elige un código Uniclass para {category}:", PickItemsFor(category), null);
                }
                SetStatus("Consultando sugerencia de la IA…");
                var res = await _app.Backend.SuggestClassificationAsync(issue.Element);
                var items = PickItemsFor(category);
                string prompt;
                string? preselect = null;
                if (res.Ok && res.Value is { } s)
                {
                    if (items.Count == 0)
                    {
                        items = s.Candidates.Select(c => new Dialogs.PickItem(c.Code, $"{c.Code} — {c.TitleEs}")).ToList();
                    }
                    preselect = s.SuggestedCode;
                    prompt = s.SuggestedCode is null
                        ? "La IA no encontró un código seguro. Elige uno de la tabla:"
                        : $"La IA sugiere {s.SuggestedCode}" + (string.IsNullOrWhiteSpace(s.Reason) ? "." : $": {s.Reason}") + " Confirma o elige otro:";
                    SetStatus($"Sugerencia recibida (modo {s.Mode}).");
                }
                else
                {
                    prompt = "La IA no está disponible. Elige un código de la tabla local:";
                    SetStatus("IA no disponible: " + res.Error);
                }
                return Dialogs.Pick(this, title, prompt, items, preselect);
            }

            default:
                return Dialogs.AskText(this, title, $"Valor para \"{parameter}\":", current);
        }
    }

    private List<Dialogs.PickItem> PickItemsFor(string category) =>
        _app.Engine.Uniclass.ForCategory(category).Select(u => new Dialogs.PickItem(u.Code, u.Display)).ToList();

    // ---------- Microencuesta ----------

    private async void OnFeedback(object sender, RoutedEventArgs e)
    {
        if (Selected is not { } item)
        {
            return;
        }
        var issue = item.Issue;
        var answer = Dialogs.AskFeedback(this, $"{issue.RuleId} · {issue.Rule.Name}");
        if (answer is null)
        {
            return;
        }
        var ids = _app.Session.BackendIdsFor(issue.ElementGuid, issue.RuleId);
        var feedback = new FeedbackCreate
        {
            // element_guid es obligatorio en el contrato: para reglas de documento se envía "DOC:<archivo>".
            ElementGuid = issue.ElementGuid ?? "DOC:" + _app.Session.FileName,
            RuleId = issue.RuleId,
            IssueId = ids.Length > 0 ? ids[0] : null,
            Reason = answer.Value.Reason,
            Comment = answer.Value.Comment,
            Author = _app.Session.Author,
        };
        FeedbackButton.IsEnabled = false;
        try
        {
            SetStatus("Enviando comentario…");
            var res = await _app.Backend.CreateFeedbackAsync(feedback);
            SetStatus(res.Ok ? "¡Gracias! Comentario registrado." : "No se pudo enviar el comentario: " + res.Error);
        }
        finally
        {
            FeedbackButton.IsEnabled = true;
        }
    }

    // ---------- utilidades ----------

    private static Document RequireDocument(UIApplication app)
    {
        var doc = app.ActiveUIDocument?.Document ?? throw new InvalidOperationException("No hay un documento activo.");
        if (doc.IsFamilyDocument)
        {
            throw new InvalidOperationException("Profesor BIM valida modelos de proyecto, no familias.");
        }
        return doc;
    }

    private async Task RunGuarded(Func<Task> work)
    {
        if (_busy)
        {
            SetStatus("Espera a que termine la operación en curso…");
            return;
        }
        _busy = true;
        ValidateButton.IsEnabled = SendButton.IsEnabled = FixButton.IsEnabled = false;
        try
        {
            await work();
        }
        catch (Exception ex)
        {
            SetStatus(ex.Message);
        }
        finally
        {
            _busy = false;
            ValidateButton.IsEnabled = SendButton.IsEnabled = FixButton.IsEnabled = true;
        }
    }
}
