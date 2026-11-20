using System.Text.Json;
using ProfesorBim.Core.Api;

namespace ProfesorBim.Core.Rules;

public static class RuleSetLoader
{
    public static RuleSet Load(string path) => Parse(File.ReadAllText(path));

    public static RuleSet Parse(string json) =>
        JsonSerializer.Deserialize(json, ProfesorBimJsonContext.Default.RuleSet)
        ?? throw new InvalidDataException("rules.json vacío o inválido.");

    /// <summary>
    /// Resuelve la ruta de la tabla Uniclass: explícita, relativa a <paramref name="baseDir"/>,
    /// o relativa a la raíz del repo (carpeta padre de la carpeta de rules.json).
    /// </summary>
    public static string ResolveUniclassPath(RuleSet rules, string rulesPath, string baseDir, string? explicitPath)
    {
        var candidates = new List<string>();
        if (!string.IsNullOrWhiteSpace(explicitPath))
        {
            candidates.Add(Path.IsPathRooted(explicitPath) ? explicitPath : Path.Combine(baseDir, explicitPath));
        }
        var table = rules.Classification.TableFile.Replace('/', Path.DirectorySeparatorChar);
        candidates.Add(Path.Combine(baseDir, table));
        var rulesDir = Path.GetDirectoryName(Path.GetFullPath(rulesPath)) ?? baseDir;
        candidates.Add(Path.Combine(rulesDir, "..", table));
        candidates.Add(Path.Combine(rulesDir, Path.GetFileName(table)));
        return candidates.FirstOrDefault(File.Exists) ?? candidates[0];
    }
}
