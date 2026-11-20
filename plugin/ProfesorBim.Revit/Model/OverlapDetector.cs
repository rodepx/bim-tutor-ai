using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using ProfesorBim.Core.Model;
using ProfesorBim.Core.Rules;

namespace ProfesorBim.Revit.Model;

/// <summary>
/// Detección geométrica de no_overlap: ElementIntersectsElementFilter entre category_a y category_b,
/// con prefiltro rápido por BoundingBox. Marca los pares ya unidos (JoinGeometryUtils.AreElementsJoined).
/// </summary>
public static class OverlapDetector
{
    /// <param name="subset">null = todo el modelo; si no, solo pares donde participa algún elemento del subconjunto.</param>
    public static List<OverlapPair> Find(Document doc, RuleSet rules, ICollection<ElementId>? subset)
    {
        var result = new List<OverlapPair>();
        foreach (var rule in rules.EnabledRules.Where(r => r.Check == RuleChecks.NoOverlap))
        {
            if (!Enum.TryParse<BuiltInCategory>(rule.GetString("category_a") ?? "", out var catA)
                || !Enum.TryParse<BuiltInCategory>(rule.GetString("category_b") ?? "", out var catB))
            {
                continue;
            }

            IEnumerable<Element> sourcesA;
            IEnumerable<Element> sourcesB;
            if (subset is null)
            {
                sourcesA = new FilteredElementCollector(doc).OfCategory(catA).WhereElementIsNotElementType().ToElements();
                sourcesB = Array.Empty<Element>();
            }
            else
            {
                var elems = subset.Select(doc.GetElement).Where(e => e is not null && e is not ElementType && e.Category is not null).ToList();
                sourcesA = elems.Where(e => e.Category!.BuiltInCategory == catA);
                sourcesB = elems.Where(e => e.Category!.BuiltInCategory == catB);
            }

            foreach (var a in sourcesA)
            {
                foreach (var b in Intersecting(doc, a, catB))
                {
                    result.Add(new OverlapPair(a.UniqueId, b.UniqueId, JoinGeometryUtils.AreElementsJoined(doc, a, b)));
                }
            }
            foreach (var b in sourcesB)
            {
                foreach (var a in Intersecting(doc, b, catA))
                {
                    result.Add(new OverlapPair(a.UniqueId, b.UniqueId, JoinGeometryUtils.AreElementsJoined(doc, a, b)));
                }
            }
        }
        return result;
    }

    private static IEnumerable<Element> Intersecting(Document doc, Element source, BuiltInCategory otherCategory)
    {
        var bb = source.get_BoundingBox(null);
        if (bb is null)
        {
            return Array.Empty<Element>();
        }
        try
        {
            return new FilteredElementCollector(doc)
                .OfCategory(otherCategory)
                .WhereElementIsNotElementType()
                .WherePasses(new BoundingBoxIntersectsFilter(new Outline(bb.Min, bb.Max)))
                .WherePasses(new ElementIntersectsElementFilter(source))
                .Where(e => e.Id != source.Id)
                .ToList();
        }
        catch (Autodesk.Revit.Exceptions.ArgumentException)
        {
            // Elemento sin geometría sólida soportada por el filtro.
            return Array.Empty<Element>();
        }
    }
}
