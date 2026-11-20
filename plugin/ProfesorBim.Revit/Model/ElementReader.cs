using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Autodesk.Revit.DB;
using ProfesorBim.Core.Model;
using ProfesorBim.Core.Rules;

namespace ProfesorBim.Revit.Model;

/// <summary>Lee elementos Revit y los convierte a <see cref="ElementData"/> (unidades SI).</summary>
public sealed class ElementReader
{
    private static readonly BuiltInParameter[] LevelParams =
    [
        BuiltInParameter.INSTANCE_REFERENCE_LEVEL_PARAM,
        BuiltInParameter.FAMILY_BASE_LEVEL_PARAM,
        BuiltInParameter.FAMILY_LEVEL_PARAM,
        BuiltInParameter.WALL_BASE_CONSTRAINT,
        BuiltInParameter.SCHEDULE_LEVEL_PARAM,
        BuiltInParameter.LEVEL_PARAM,
        BuiltInParameter.INSTANCE_SCHEDULE_ONLY_LEVEL_PARAM,
    ];

    private static readonly BuiltInParameter[] WidthParams =
        [BuiltInParameter.DOOR_WIDTH, BuiltInParameter.WINDOW_WIDTH, BuiltInParameter.FAMILY_WIDTH_PARAM, BuiltInParameter.GENERIC_WIDTH];

    private static readonly BuiltInParameter[] HeightParams =
        [BuiltInParameter.DOOR_HEIGHT, BuiltInParameter.WINDOW_HEIGHT, BuiltInParameter.FAMILY_HEIGHT_PARAM, BuiltInParameter.GENERIC_HEIGHT];

    private readonly RuleSet _rules;
    private readonly Dictionary<BuiltInCategory, string> _categories;

    public ElementReader(RuleSet rules)
    {
        _rules = rules;
        _categories = new Dictionary<BuiltInCategory, string>();
        foreach (var name in rules.AllCategories())
        {
            if (Enum.TryParse<BuiltInCategory>(name, out var bic))
            {
                _categories[bic] = name;
            }
        }
    }

    public ICollection<BuiltInCategory> Categories => _categories.Keys;

    public ElementMulticategoryFilter CategoryFilter() => new(_categories.Keys.ToList());

    public bool IsTracked(Element e) =>
        e is not ElementType && e.Category is { } c && _categories.ContainsKey(c.BuiltInCategory) && e.ViewSpecific == false;

    /// <summary>Todas las instancias (no tipos) de las categorías de rules.json.</summary>
    public IList<Element> CollectAll(Document doc) =>
        _categories.Count == 0
            ? new List<Element>()
            : new FilteredElementCollector(doc)
            .WherePasses(CategoryFilter())
            .WhereElementIsNotElementType()
            .Where(IsTracked)
            .ToList();

    public ElementData Read(Element e)
    {
        var doc = e.Document;
        var bic = e.Category?.BuiltInCategory ?? BuiltInCategory.INVALID;
        var category = _categories.TryGetValue(bic, out var n) ? n : bic.ToString();
        var type = doc.GetElement(e.GetTypeId()) as ElementType;

        var data = new ElementData
        {
            Guid = e.UniqueId,
            ElementId = e.Id.Value,
            Category = category,
            Discipline = _rules.DisciplineOf(category),
            FamilyName = type?.FamilyName,
            TypeName = type?.Name ?? e.Name,
            TypeElementId = type?.Id.Value,
            Level = LevelName(e),
        };

        foreach (var name in _rules.ClassificationParameterNames())
        {
            var value = GetText(type, name) ?? GetText(e, name);
            if (value is not null)
            {
                data.ClassificationCode = value;
                data.ClassificationParameterFound = name;
                break;
            }
        }

        data.Parameters[_rules.Classification.ParameterName] = data.ClassificationCode;
        foreach (var p in _rules.RequiredParametersFor(category))
        {
            data.Parameters[p] = GetText(e, p) ?? GetText(type, p);
        }

        ReadQuantities(e, type, bic, data);
        return data;
    }

    private static void ReadQuantities(Element e, ElementType? type, BuiltInCategory bic, ElementData data)
    {
        if (bic is BuiltInCategory.OST_Doors or BuiltInCategory.OST_Windows)
        {
            var w = FirstDouble(e, WidthParams) ?? FirstDouble(type, WidthParams);
            var h = FirstDouble(e, HeightParams) ?? FirstDouble(type, HeightParams);
            if (w is > 0 && h is > 0)
            {
                data.AreaM2 = Round(UnitUtils.ConvertFromInternalUnits(w.Value * h.Value, UnitTypeId.SquareMeters));
            }
            return;
        }

        var vol = FirstDouble(e, [BuiltInParameter.HOST_VOLUME_COMPUTED]);
        if (vol is > 0)
        {
            data.VolumeM3 = Round(UnitUtils.ConvertFromInternalUnits(vol.Value, UnitTypeId.CubicMeters));
        }
        var area = FirstDouble(e, [BuiltInParameter.HOST_AREA_COMPUTED]);
        if (area is > 0)
        {
            data.AreaM2 = Round(UnitUtils.ConvertFromInternalUnits(area.Value, UnitTypeId.SquareMeters));
        }
        var len = FirstDouble(e, [BuiltInParameter.CURVE_ELEM_LENGTH, BuiltInParameter.INSTANCE_LENGTH_PARAM]);
        if (len is > 0)
        {
            data.LengthM = Round(UnitUtils.ConvertFromInternalUnits(len.Value, UnitTypeId.Meters));
        }
    }

    private static string? LevelName(Element e)
    {
        var doc = e.Document;
        if (e.LevelId != ElementId.InvalidElementId && doc.GetElement(e.LevelId) is Level lvl)
        {
            return lvl.Name;
        }
        foreach (var bip in LevelParams)
        {
            var p = e.get_Parameter(bip);
            if (p is { StorageType: StorageType.ElementId })
            {
                var id = p.AsElementId();
                if (id != ElementId.InvalidElementId && doc.GetElement(id) is Level l)
                {
                    return l.Name;
                }
            }
        }
        return null;
    }

    private static double? FirstDouble(Element? e, BuiltInParameter[] bips)
    {
        if (e is null)
        {
            return null;
        }
        foreach (var bip in bips)
        {
            var p = e.get_Parameter(bip);
            if (p is { HasValue: true, StorageType: StorageType.Double })
            {
                return p.AsDouble();
            }
        }
        return null;
    }

    /// <summary>Valor de un parámetro por nombre como texto; null si no existe o está vacío.</summary>
    public static string? GetText(Element? e, string name)
    {
        var p = e?.LookupParameter(name);
        if (p is null || !p.HasValue)
        {
            return null;
        }
        var text = p.StorageType switch
        {
            StorageType.String => p.AsString(),
            StorageType.Integer => p.AsValueString() ?? p.AsInteger().ToString(CultureInfo.InvariantCulture),
            StorageType.Double => p.AsValueString() ?? p.AsDouble().ToString(CultureInfo.InvariantCulture),
            StorageType.ElementId => p.AsValueString(),
            _ => null,
        };
        return string.IsNullOrWhiteSpace(text) ? null : text.Trim();
    }

    private static double Round(double v) => Math.Round(v, 4);
}
