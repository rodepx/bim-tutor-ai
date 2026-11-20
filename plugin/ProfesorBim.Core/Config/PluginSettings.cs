using System.Text.Json;
using ProfesorBim.Core.Api;

namespace ProfesorBim.Core.Config;

/// <summary>
/// profesorbim.settings.json junto a la DLL. Rutas relativas se resuelven desde la carpeta de la DLL.
/// No guardar secretos aquí.
/// </summary>
public sealed class PluginSettings
{
    public const string FileName = "profesorbim.settings.json";

    public string BaseUrl { get; set; } = "http://localhost:8000/api";

    public int TimeoutSeconds { get; set; } = 10;

    /// <summary>Tiempo sin cambios antes de revalidar en vivo (ms).</summary>
    public int LiveValidationDebounceMs { get; set; } = 600;

    public bool LiveValidation { get; set; } = true;

    public string RulesPath { get; set; } = "data/rules.json";

    /// <summary>Opcional: si es null se usa classification.table_file de rules.json.</summary>
    public string? UniclassPath { get; set; }

    public static PluginSettings LoadOrDefault(string directory)
    {
        var path = Path.Combine(directory, FileName);
        try
        {
            if (File.Exists(path))
            {
                return JsonSerializer.Deserialize(File.ReadAllText(path), ProfesorBimJsonContext.Default.PluginSettings) ?? new PluginSettings();
            }
        }
        catch (Exception)
        {
            // Archivo corrupto: se usan valores por defecto.
        }
        return new PluginSettings();
    }

    public string ResolvePath(string directory, string path) =>
        Path.IsPathRooted(path) ? path : Path.GetFullPath(Path.Combine(directory, path.Replace('/', Path.DirectorySeparatorChar)));
}
