using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Autodesk.Revit.DB;
using ProfesorBim.Core.Api;
using ProfesorBim.Core.Model;
using ProfesorBim.Core.Rules;

namespace ProfesorBim.Revit.Model;

/// <summary>
/// Estado de validación del documento activo. Todos los métodos que reciben Document se llaman
/// en contexto de API de Revit (hilo principal). Los ids del backend se escriben desde hilos de fondo (concurrente).
/// </summary>
public sealed class ValidationSession
{
    private readonly Dictionary<string, ElementData> _elements = new(StringComparer.Ordinal);
    private readonly Dictionary<long, string> _idToGuid = new();
    private List<ValidationIssue> _elementIssues = new();
    private List<ValidationIssue> _documentIssues = new();

    /// <summary>"guid|rule_id" → ids de issues abiertos en el backend (último snapshot enviado).</summary>
    private readonly ConcurrentDictionary<string, int[]> _backendIds = new(StringComparer.Ordinal);

    public ValidationSession(RuleEngine engine)
    {
        Engine = engine;
        Reader = new ElementReader(engine.Rules);
    }

    public RuleEngine Engine { get; }

    public ElementReader Reader { get; }

    public string? DocumentKey { get; private set; }

    public string FileName { get; private set; } = "";

    public string? Author { get; private set; }

    /// <summary>Se dispara en el hilo de Revit tras cada validación.</summary>
    public event Action? IssuesChanged;

    public IReadOnlyList<ValidationIssue> Issues => _documentIssues.Concat(_elementIssues).ToList();

    public IReadOnlyCollection<ElementData> Elements => _elements.Values;

    public static string KeyOf(Document doc) => string.IsNullOrEmpty(doc.PathName) ? "title:" + doc.Title : doc.PathName;

    public static string FileNameOf(Document doc) =>
        RuleEngine.StripExtension(string.IsNullOrEmpty(doc.PathName) ? doc.Title : Path.GetFileNameWithoutExtension(doc.PathName));

    public bool IsCurrent(Document doc) => DocumentKey is not null && DocumentKey == KeyOf(doc);

    public void Clear()
    {
        DocumentKey = null;
        FileName = "";
        _elements.Clear();
        _idToGuid.Clear();
        _elementIssues = new();
        _documentIssues = new();
        _backendIds.Clear();
        IssuesChanged?.Invoke();
    }

    /// <summary>Validación completa del documento.</summary>
    public void ValidateAll(Document doc)
    {
        if (!IsCurrent(doc))
        {
            _backendIds.Clear();
        }
        DocumentKey = KeyOf(doc);
        FileName = FileNameOf(doc);
        Author = doc.Application.Username;
        _elements.Clear();
        _idToGuid.Clear();

        foreach (var e in Reader.CollectAll(doc))
        {
            var data = Reader.Read(e);
            _elements[data.Guid] = data;
            _idToGuid[e.Id.Value] = data.Guid;
        }

        var overlaps = OverlapDetector.Find(doc, Engine.Rules, null);
        _elementIssues = Engine.ValidateElements(_elements.Values, overlaps);
        _documentIssues = Engine.ValidateDocument(FileName);
        IssuesChanged?.Invoke();
    }

    /// <summary>Revalida solo los elementos cambiados (y las instancias de tipos cambiados).</summary>
    public void Revalidate(Document doc, ICollection<ElementId> changed, ICollection<ElementId> deleted)
    {
        if (!IsCurrent(doc))
        {
            ValidateAll(doc);
            return;
        }

        var affectedIds = ExpandAffected(doc, changed);
        var removedGuids = new HashSet<string>(StringComparer.Ordinal);
        foreach (var id in deleted)
        {
            if (_idToGuid.Remove(id.Value, out var g))
            {
                removedGuids.Add(g);
                _elements.Remove(g);
            }
        }

        var updated = new List<ElementData>();
        foreach (var id in affectedIds)
        {
            var e = doc.GetElement(id);
            if (e is null || !Reader.IsTracked(e))
            {
                if (_idToGuid.Remove(id.Value, out var g))
                {
                    removedGuids.Add(g);
                    _elements.Remove(g);
                }
                continue;
            }
            var data = Reader.Read(e);
            _elements[data.Guid] = data;
            _idToGuid[id.Value] = data.Guid;
            updated.Add(data);
            removedGuids.Add(data.Guid);
        }

        var newFileName = FileNameOf(doc);
        var fileChanged = newFileName != FileName;
        if (removedGuids.Count == 0 && !fileChanged)
        {
            return;
        }

        // Fuera: todos los issues de los elementos afectados, y los no_overlap que los citan como "otro".
        _elementIssues.RemoveAll(i =>
            (i.ElementGuid is not null && removedGuids.Contains(i.ElementGuid))
            || (i.RelatedGuid is not null && removedGuids.Contains(i.RelatedGuid)));

        _elementIssues.AddRange(Engine.ValidateElements(updated));
        var trackedIds = affectedIds.Where(id => _idToGuid.ContainsKey(id.Value)).ToList();
        if (trackedIds.Count > 0)
        {
            var pairs = OverlapDetector.Find(doc, Engine.Rules, trackedIds);
            var known = pairs.SelectMany(p => new[] { p.GuidA, p.GuidB })
                .Distinct()
                .Select(g => _elements.TryGetValue(g, out var d) ? d : null)
                .Where(d => d is not null)
                .Cast<ElementData>();
            _elementIssues.AddRange(Engine.ValidateOverlaps(known, pairs));
        }

        FileName = newFileName;
        _documentIssues = Engine.ValidateDocument(FileName);
        IssuesChanged?.Invoke();
    }

    private HashSet<ElementId> ExpandAffected(Document doc, ICollection<ElementId> changed)
    {
        var result = new HashSet<ElementId>();
        var changedTypes = new HashSet<ElementId>();
        foreach (var id in changed)
        {
            var e = doc.GetElement(id);
            if (e is ElementType)
            {
                changedTypes.Add(id);
            }
            else if (e is not null)
            {
                result.Add(id);
            }
            else
            {
                result.Add(id); // borrado dentro de la misma tanda: se limpia en Revalidate
            }
        }

        if (changedTypes.Count > 0)
        {
            foreach (var inst in Reader.CollectAll(doc))
            {
                if (changedTypes.Contains(inst.GetTypeId()))
                {
                    result.Add(inst.Id);
                }
            }
        }
        return result;
    }

    public ElementData? FindElement(string guid) => _elements.TryGetValue(guid, out var d) ? d : null;

    public bool HasIssue(string key) => _elementIssues.Any(i => i.Key == key) || _documentIssues.Any(i => i.Key == key);

    public bool HasIssueFor(string? elementGuid, string ruleId) =>
        Issues.Any(i => i.ElementGuid == elementGuid && i.RuleId == ruleId);

    public SnapshotCreate BuildSnapshot(string cdeState) =>
        SnapshotFactory.Create(FileName, cdeState, Engine.Rules.Version, Author, _elements.Values, Issues, DateTime.Now);

    // ---- ids del backend ----

    public static string BackendKey(string? guid, string ruleId) => $"{guid ?? ""}|{ruleId}";

    public void SetBackendIssues(IEnumerable<Issue> issues)
    {
        _backendIds.Clear();
        foreach (var g in issues.GroupBy(i => BackendKey(i.ElementGuid, i.RuleId)))
        {
            _backendIds[g.Key] = g.Select(i => i.Id).ToArray();
        }
    }

    public int[] BackendIdsFor(string? guid, string ruleId) =>
        _backendIds.TryGetValue(BackendKey(guid, ruleId), out var ids) ? ids : Array.Empty<int>();

    public void ForgetBackendIds(string? guid, string ruleId) => _backendIds.TryRemove(BackendKey(guid, ruleId), out _);
}
