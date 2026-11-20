using System.Text;

namespace ProfesorBim.Core.Rules;

/// <summary>Fila de data/uniclass_subset.csv.</summary>
public sealed record UniclassEntry(string Code, string TitleEs, string TitleEn, string Table, IReadOnlyList<string> RevitCategories, string Estado)
{
    public string Display => $"{Code} — {TitleEs}";
}

/// <summary>Tabla Uniclass del proyecto (subconjunto Ss).</summary>
public sealed class UniclassTable
{
    private readonly Dictionary<string, UniclassEntry> _byCode;

    public UniclassTable(IEnumerable<UniclassEntry> entries)
    {
        // Sensible a mayúsculas como el backend (services/budget.py): "ss_25_10_20" no existe en la tabla
        // y debe dar R03 aquí, no pasar la validación y caer luego en "codigo_invalido" del 5D.
        _byCode = new Dictionary<string, UniclassEntry>(StringComparer.Ordinal);
        foreach (var e in entries)
        {
            _byCode[e.Code] = e;
        }
    }

    public IReadOnlyCollection<UniclassEntry> All => _byCode.Values;

    public UniclassEntry? Find(string code) => _byCode.TryGetValue(code.Trim(), out var e) ? e : null;

    public bool Exists(string code) => Find(code) is not null;

    /// <summary>true si el código existe y la categoría Revit está permitida para él.</summary>
    public bool IsValidFor(string code, string category) =>
        Find(code) is { } e && e.RevitCategories.Contains(category, StringComparer.Ordinal);

    public IReadOnlyList<UniclassEntry> ForCategory(string category) =>
        _byCode.Values.Where(e => e.RevitCategories.Contains(category, StringComparer.Ordinal)).OrderBy(e => e.Code, StringComparer.Ordinal).ToList();

    public static UniclassTable Load(string path) => Parse(File.ReadAllText(path, Encoding.UTF8));

    public static UniclassTable Parse(string csv)
    {
        var lines = csv.Replace("\r\n", "\n").Split('\n');
        var entries = new List<UniclassEntry>();
        if (lines.Length == 0)
        {
            return new UniclassTable(entries);
        }

        var header = SplitCsvLine(lines[0]).Select(h => h.Trim().TrimStart('﻿')).ToList();
        int Col(string name) => header.FindIndex(h => string.Equals(h, name, StringComparison.OrdinalIgnoreCase));
        int iCode = Col("code"), iEs = Col("title_es"), iEn = Col("title_en"), iTable = Col("table"), iCats = Col("revit_categories"), iEstado = Col("estado");

        foreach (var raw in lines.Skip(1))
        {
            if (string.IsNullOrWhiteSpace(raw))
            {
                continue;
            }
            var f = SplitCsvLine(raw);
            string Get(int i) => i >= 0 && i < f.Count ? f[i].Trim() : "";
            var code = Get(iCode);
            if (code.Length == 0)
            {
                continue;
            }
            var cats = Get(iCats).Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
            entries.Add(new UniclassEntry(code, Get(iEs), Get(iEn), Get(iTable), cats, Get(iEstado)));
        }
        return new UniclassTable(entries);
    }

    /// <summary>CSV mínimo con soporte de comillas dobles.</summary>
    private static List<string> SplitCsvLine(string line)
    {
        var result = new List<string>();
        var sb = new StringBuilder();
        var inQuotes = false;
        for (var i = 0; i < line.Length; i++)
        {
            var c = line[i];
            if (inQuotes)
            {
                if (c == '"' && i + 1 < line.Length && line[i + 1] == '"')
                {
                    sb.Append('"');
                    i++;
                }
                else if (c == '"')
                {
                    inQuotes = false;
                }
                else
                {
                    sb.Append(c);
                }
            }
            else if (c == '"')
            {
                inQuotes = true;
            }
            else if (c == ',')
            {
                result.Add(sb.ToString());
                sb.Clear();
            }
            else
            {
                sb.Append(c);
            }
        }
        result.Add(sb.ToString());
        return result;
    }
}
