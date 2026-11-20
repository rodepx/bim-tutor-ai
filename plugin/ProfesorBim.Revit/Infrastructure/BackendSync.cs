using System;
using System.Linq;
using System.Threading.Tasks;
using ProfesorBim.Core.Api;
using ProfesorBim.Revit.Model;
using ProfesorBim.Revit.UI;

namespace ProfesorBim.Revit.Infrastructure;

/// <summary>Operaciones con el backend que corren en hilos de fondo y reportan al panel. Nunca bloquean Revit.</summary>
public sealed class BackendSync
{
    private readonly BackendClient _client;
    private readonly ValidationSession _session;
    private readonly IssuesPanel _panel;
    private int _sending;

    public BackendSync(BackendClient client, ValidationSession session, IssuesPanel panel)
    {
        _client = client;
        _session = session;
        _panel = panel;
    }

    /// <summary>POST /snapshots y luego GET /issues para conocer los ids de backend (para PATCH tras un fix).</summary>
    public Task SendSnapshotAsync(SnapshotCreate snapshot)
    {
        if (System.Threading.Interlocked.Exchange(ref _sending, 1) == 1)
        {
            _panel.SetStatus("Ya hay un envío en curso…");
            return Task.CompletedTask;
        }
        _panel.SetStatus($"Enviando snapshot {snapshot.VersionLabel} ({snapshot.CdeState}, {snapshot.Elements.Count} elementos, {snapshot.Issues.Count} issues)…");
        return Task.Run(async () =>
        {
            try
            {
                var result = await _client.CreateSnapshotAsync(snapshot).ConfigureAwait(false);
                if (!result.Ok || result.Value is null)
                {
                    _panel.SetStatus($"Sin conexión con el backend: {result.Error} (la validación local sigue funcionando).");
                    return;
                }
                var snap = result.Value;
                var issues = await _client.ListIssuesAsync(snap.Id, IssueStatuses.Open).ConfigureAwait(false);
                if (issues.Ok && issues.Value is not null)
                {
                    _session.SetBackendIssues(issues.Value);
                }
                _panel.SetStatus($"Snapshot #{snap.Id} enviado ({snap.ProjectCode} {snap.VersionLabel}, {snap.CdeState}): " +
                                 $"{snap.ElementCount} elementos, {snap.OpenIssueCount} issues abiertos." +
                                 (issues.Ok ? "" : " (No se pudieron leer los ids de issues: " + issues.Error + ")"));
            }
            catch (Exception ex)
            {
                _panel.SetStatus("Error al enviar: " + ex.Message);
            }
            finally
            {
                System.Threading.Interlocked.Exchange(ref _sending, 0);
            }
        });
    }

    /// <summary>PATCH /issues/{id} status=fixed, fixed_by=one_click para los issues de backend del elemento+regla.</summary>
    public async Task MarkFixedAsync(string? elementGuid, string ruleId)
    {
        var ids = _session.BackendIdsFor(elementGuid, ruleId);
        if (ids.Length == 0)
        {
            return;
        }
        var results = await Task.WhenAll(ids.Select(id => _client.UpdateIssueAsync(id, IssueStatuses.Fixed, "one_click"))).ConfigureAwait(false);
        var failed = results.Where(r => !r.Ok).ToList();
        if (failed.Count == 0)
        {
            _session.ForgetBackendIds(elementGuid, ruleId);
            _panel.SetStatus($"Corregido y registrado en el backend (issue {string.Join(", ", ids.Select(i => "#" + i))}).");
        }
        else
        {
            _panel.SetStatus("Corregido en el modelo; el backend no respondió: " + failed[0].Error);
        }
    }
}
