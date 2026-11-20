using System;
using System.Collections.Generic;
using System.Diagnostics;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;

namespace ProfesorBim.Revit.Model;

/// <summary>
/// Validación en vivo: DocumentChanged solo acumula ids (barato); en Idling, tras un periodo sin cambios
/// (debounce), se revalidan en lote solo los elementos cambiados. Así no se frena el modelado.
/// </summary>
public sealed class LiveValidation
{
    private readonly ValidationSession _session;
    private readonly TimeSpan _debounce;
    private readonly HashSet<ElementId> _changed = new();
    private readonly HashSet<ElementId> _deleted = new();
    private readonly Stopwatch _sinceLastChange = new();

    public LiveValidation(ValidationSession session, TimeSpan debounce, bool enabled)
    {
        _session = session;
        _debounce = debounce;
        Enabled = enabled;
    }

    public bool Enabled { get; set; }

    /// <summary>Error de la última revalidación (para mostrar en el panel).</summary>
    public event Action<string>? Failed;

    public void OnDocumentChanged(object? sender, DocumentChangedEventArgs e)
    {
        if (!Enabled)
        {
            return;
        }
        var doc = e.GetDocument();
        if (doc is null || doc.IsFamilyDocument || !_session.IsCurrent(doc))
        {
            return;
        }
        _changed.UnionWith(e.GetAddedElementIds());
        _changed.UnionWith(e.GetModifiedElementIds());
        _deleted.UnionWith(e.GetDeletedElementIds());
        _sinceLastChange.Restart();
    }

    public void OnIdling(object? sender, IdlingEventArgs e)
    {
        if (_changed.Count == 0 && _deleted.Count == 0)
        {
            return;
        }
        if (_sinceLastChange.Elapsed < _debounce)
        {
            // Pedir otro Idling pronto; solo mientras hay cambios pendientes.
            e.SetRaiseWithoutDelay();
            return;
        }
        if (sender is UIApplication app && app.ActiveUIDocument?.Document is { } doc)
        {
            Flush(doc);
        }
    }

    /// <summary>Procesa ya los cambios pendientes (más ids extra). Llamar en contexto de API.</summary>
    public void Flush(Document doc, IEnumerable<ElementId>? extraChanged = null)
    {
        var changed = new List<ElementId>(_changed);
        var deleted = new List<ElementId>(_deleted);
        if (extraChanged is not null)
        {
            changed.AddRange(extraChanged);
        }
        _changed.Clear();
        _deleted.Clear();
        _sinceLastChange.Reset();
        if (changed.Count == 0 && deleted.Count == 0)
        {
            return;
        }
        try
        {
            if (_session.IsCurrent(doc))
            {
                _session.Revalidate(doc, changed, deleted);
            }
        }
        catch (Exception ex)
        {
            Failed?.Invoke("Error en validación en vivo: " + ex.Message);
        }
    }

    public void Reset()
    {
        _changed.Clear();
        _deleted.Clear();
        _sinceLastChange.Reset();
    }
}
