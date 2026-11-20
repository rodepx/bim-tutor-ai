using System;
using System.Collections.Generic;
using System.Globalization;
using Autodesk.Revit.DB;

namespace ProfesorBim.Revit.Model;

public sealed record FixResult(bool Ok, string Message, IReadOnlyList<ElementId> Affected)
{
    public static FixResult Fail(string message) => new(false, message, Array.Empty<ElementId>());
}

/// <summary>Correcciones en 1 clic. Cada método abre su propia Transaction. Llamar SOLO en contexto de API (ExternalEvent).</summary>
public static class FixService
{
    public static FixResult RenameType(Document doc, long typeId, string newName)
    {
        if (string.IsNullOrWhiteSpace(newName))
        {
            return FixResult.Fail("El nombre no puede estar vacío.");
        }
        if (doc.GetElement(new ElementId(typeId)) is not ElementType type)
        {
            return FixResult.Fail("No se encontró el tipo del elemento.");
        }
        return InTransaction(doc, "Profesor BIM: renombrar tipo", () =>
        {
            type.Name = newName.Trim();
            return new FixResult(true, $"Tipo renombrado a \"{type.Name}\".", [type.Id]);
        });
    }

    /// <summary>
    /// Escribe el primer parámetro existente de <paramref name="parameterNames"/>: en el tipo si
    /// <paramref name="preferType"/> (clasificación, BEP §4), si no en la instancia; con respaldo en el otro.
    /// </summary>
    public static FixResult SetParameter(Document doc, long elementId, IReadOnlyList<string> parameterNames, string value, bool preferType)
    {
        if (doc.GetElement(new ElementId(elementId)) is not { } element)
        {
            return FixResult.Fail("El elemento ya no existe.");
        }
        var type = doc.GetElement(element.GetTypeId()) as ElementType;
        Element[] order = type is null ? [element] : preferType ? [type, element] : [element, type];

        Parameter? param = null;
        Element target = element;
        string parameterName = parameterNames.Count > 0 ? parameterNames[0] : "";
        foreach (var name in parameterNames)
        {
            foreach (var candidate in order)
            {
                param = Writable(candidate.LookupParameter(name));
                if (param is not null)
                {
                    target = candidate;
                    parameterName = name;
                    break;
                }
            }
            if (param is not null)
            {
                break;
            }
        }
        if (param is null)
        {
            return FixResult.Fail($"El parámetro \"{parameterName}\" no existe (o es de solo lectura) en el elemento ni en su tipo. " +
                                  "Agrégalo como parámetro compartido del proyecto.");
        }

        var p = param;
        return InTransaction(doc, $"Profesor BIM: {parameterName}", () =>
        {
            var ok = p.StorageType switch
            {
                StorageType.String => p.Set(value),
                StorageType.Integer => int.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out var i) && p.Set(i),
                StorageType.Double => p.SetValueString(value)
                                      || (double.TryParse(value.Replace(',', '.'), NumberStyles.Float, CultureInfo.InvariantCulture, out var d) && p.Set(d)),
                _ => false,
            };
            if (!ok)
            {
                throw new InvalidOperationException($"No se pudo asignar \"{value}\" a {parameterName} ({p.StorageType}).");
            }
            var where = target is ElementType ? "tipo (afecta a todas sus instancias)" : "elemento";
            return new FixResult(true, $"{parameterName} = \"{value}\" en el {where}.", [target.Id, element.Id]);
        });
    }

    public static FixResult JoinGeometry(Document doc, long elementId, string otherGuid)
    {
        var a = doc.GetElement(new ElementId(elementId));
        var b = doc.GetElement(otherGuid);
        if (a is null || b is null)
        {
            return FixResult.Fail("Uno de los elementos ya no existe.");
        }
        if (JoinGeometryUtils.AreElementsJoined(doc, a, b))
        {
            return new FixResult(true, "Los elementos ya estaban unidos.", [a.Id, b.Id]);
        }
        return InTransaction(doc, "Profesor BIM: unir geometría", () =>
        {
            JoinGeometryUtils.JoinGeometry(doc, a, b);
            return new FixResult(true, "Geometría unida.", [a.Id, b.Id]);
        });
    }

    private static Parameter? Writable(Parameter? p) => p is { IsReadOnly: false } ? p : null;

    private static FixResult InTransaction(Document doc, string name, Func<FixResult> work)
    {
        using var tx = new Transaction(doc, name);
        try
        {
            if (tx.Start() != TransactionStatus.Started)
            {
                return FixResult.Fail("No se pudo iniciar la transacción.");
            }
            var result = work();
            if (tx.Commit() != TransactionStatus.Committed)
            {
                return FixResult.Fail("Revit no aceptó el cambio (transacción revertida).");
            }
            return result;
        }
        catch (Exception ex)
        {
            if (tx.HasStarted() && !tx.HasEnded())
            {
                tx.RollBack();
            }
            return FixResult.Fail("No se pudo aplicar la corrección: " + ex.Message);
        }
    }
}
