using System.Text.Json.Nodes;
using ProfesorBim.Core.Model;
using ProfesorBim.Core.Rules;

namespace ProfesorBim.Tests;

/// <summary>Motor de reglas contra data/rules.json y data/uniclass_subset.csv con elementos falsos.</summary>
public class RuleEngineTests
{
    private static readonly string DataDir = Path.Combine(AppContext.BaseDirectory, "data");
    private static readonly string RulesPath = Path.Combine(DataDir, "rules.json");

    private static RuleEngine CreateEngine(Action<JsonObject>? mutate = null)
    {
        var json = File.ReadAllText(RulesPath);
        if (mutate is not null)
        {
            var node = JsonNode.Parse(json)!.AsObject();
            mutate(node);
            json = node.ToJsonString();
        }
        var rules = RuleSetLoader.Parse(json);
        var uniclassPath = RuleSetLoader.ResolveUniclassPath(rules, RulesPath, AppContext.BaseDirectory, null);
        return new RuleEngine(rules, UniclassTable.Load(uniclassPath));
    }

    /// <summary>Elemento que cumple todas las reglas (por defecto un muro).</summary>
    private static ElementData Valid(string category = "OST_Walls", string typeName = "MUR_CA_e25_FC210", string? code = "Ss_25_10_20")
    {
        var e = new ElementData
        {
            Guid = Guid.NewGuid().ToString(),
            ElementId = 1001,
            Category = category,
            Discipline = category.StartsWith("OST_Structural", StringComparison.Ordinal) ? "EST" : "ARQ",
            FamilyName = "Muro básico",
            TypeName = typeName,
            ClassificationCode = code,
            ClassificationParameterFound = code is null ? null : "Uniclass_Codigo",
            Level = "Nivel 1",
            VolumeM3 = 1.5,
            AreaM2 = 6,
            LengthM = 2.4,
        };
        e.Parameters["BIM_Material"] = "Concreto";
        e.Parameters["BIM_Resistencia_fc"] = "210";
        return e;
    }

    private static List<ValidationIssue> Run(RuleEngine engine, params ElementData[] elements) => engine.ValidateElements(elements);

    [Fact]
    public void Loads_rules_json_and_uniclass_table()
    {
        var engine = CreateEngine();
        Assert.Equal("0.1.0", engine.Rules.Version);
        Assert.Equal("Uniclass_Codigo", engine.Rules.Classification.ParameterName);
        Assert.Equal(7, engine.Rules.Rules.Count);
        Assert.Equal("EST", engine.Rules.DisciplineOf("OST_StructuralFraming"));
        Assert.Equal("ARQ", engine.Rules.DisciplineOf("OST_Doors"));
        Assert.Equal(12, engine.Uniclass.All.Count);
        Assert.True(engine.Uniclass.IsValidFor("Ss_20_05_65", "OST_Walls"));
        Assert.True(engine.Uniclass.IsValidFor("Ss_20_05_65", "OST_StructuralFoundation"));
        Assert.Equal(4, engine.Uniclass.ForCategory("OST_Walls").Count);
    }

    [Theory]
    [InlineData("OST_Walls", "MUR_CA_e25_FC210", "Ss_25_10_20")]
    [InlineData("OST_StructuralColumns", "COL_CA_40x40_FC210", "Ss_20_10_10")]
    [InlineData("OST_StructuralFraming", "VIG_CA_25x50_FC210", "Ss_20_10_20")]
    [InlineData("OST_Floors", "LOS_ALIG_e20", "Ss_30_10_35")]
    [InlineData("OST_Doors", "PTA_MAD_090x210", "Ss_25_30_20")]
    public void Compliant_element_has_no_issues(string category, string typeName, string code)
    {
        var engine = CreateEngine();
        Assert.Empty(Run(engine, Valid(category, typeName, code)));
    }

    // ---- type_name_not_generic (R01) ----

    [Theory]
    [InlineData("Genérico - 200mm")]
    [InlineData("Generic - 8\"")]
    [InlineData("Muro básico")]
    [InlineData("Default")]
    [InlineData("Tipo 1")]
    [InlineData("MUR_CA_e25 Copia")]
    [InlineData("MUR_CA_e25 2")]
    public void Type_name_not_generic_flags_template_names(string typeName)
    {
        var engine = CreateEngine();
        var e = Valid(typeName: typeName);
        var issue = Assert.Single(Run(engine, e));
        Assert.Equal("R01", issue.RuleId);
        Assert.Equal("error", issue.Severity);
        Assert.Equal($"El tipo \"{typeName}\" tiene un nombre genérico de plantilla.", issue.Message);
        Assert.Equal("rename_type", issue.Rule.Fix.Type);
    }

    // ---- type_name_pattern (no está en rules.json: se inyecta) ----

    [Fact]
    public void Type_name_pattern_checks_regex_per_category()
    {
        var engine = CreateEngine(root => root["rules"]!.AsArray().Add(JsonNode.Parse("""
            {
              "id": "R90", "name": "Patrón de nombre", "check": "type_name_pattern", "severity": "info",
              "scope": { "level": "element", "categories": ["OST_Walls", "OST_Doors"] },
              "params": { "patterns_by_category": { "OST_Walls": "^MUR_[A-Z]+_e\\d+" } },
              "message": "{type_name} no cumple el patrón de {category}.",
              "explanation": "x", "fix": { "type": "rename_type" }, "bep_ref": "§3", "enabled": true
            }
            """)));

        Assert.Empty(Run(engine, Valid(typeName: "MUR_CA_e25_FC210")));

        var bad = Assert.Single(Run(engine, Valid(typeName: "MURO_CA_25")));
        Assert.Equal("R90", bad.RuleId);
        Assert.Equal("MURO_CA_25 no cumple el patrón de OST_Walls.", bad.Message);

        // Categoría sin patrón definido → no se evalúa.
        Assert.Empty(Run(engine, Valid("OST_Doors", "CUALQUIER_NOMBRE", "Ss_25_30_20")));
    }

    // ---- classification_required (R02) ----

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    public void Classification_required_flags_missing_code(string? code)
    {
        var engine = CreateEngine();
        var issue = Assert.Single(Run(engine, Valid(code: code)));
        Assert.Equal("R02", issue.RuleId);
        Assert.Equal("El elemento no tiene código Uniclass en \"Uniclass_Codigo\".", issue.Message);
        Assert.Equal("Uniclass_Codigo", issue.Parameter);
        Assert.Equal("ai_suggestion", issue.Rule.Fix.ValueSource);
    }

    // ---- classification_exists (R03) ----

    [Fact]
    public void Classification_exists_flags_unknown_code()
    {
        var engine = CreateEngine();
        var issue = Assert.Single(Run(engine, Valid(code: "Ss_99_99_99")));
        Assert.Equal("R03", issue.RuleId);
        Assert.Equal("El código \"Ss_99_99_99\" no existe en la tabla Uniclass del proyecto o no corresponde a OST_Walls.", issue.Message);
    }

    [Fact]
    public void Classification_exists_flags_code_of_other_category()
    {
        var engine = CreateEngine();
        // Ss_20_10_10 = columnas; no permitido en muros.
        var issue = Assert.Single(Run(engine, Valid(code: "Ss_20_10_10")));
        Assert.Equal("R03", issue.RuleId);
        Assert.Equal("pick_list", issue.Rule.Fix.ValueSource);
    }

    [Fact]
    public void Classification_exists_accepts_multi_category_code()
    {
        var engine = CreateEngine();
        Assert.Empty(Run(engine, Valid(code: "Ss_20_05_65")));
        Assert.Empty(Run(engine, Valid("OST_StructuralFoundation", "ZAP_CA_150x150x60_FC210", "Ss_20_05_65")));
    }

    // ---- no_overlap (R04) ----

    [Fact]
    public void No_overlap_flags_unjoined_wall_beam_pair_once()
    {
        var engine = CreateEngine();
        var wall = Valid();
        var beam = Valid("OST_StructuralFraming", "VIG_CA_25x50_FC210", "Ss_20_10_20");
        var pairs = new[] { new OverlapPair(wall.Guid, beam.Guid, AreJoined: false), new OverlapPair(wall.Guid, beam.Guid, AreJoined: false) };

        var issue = Assert.Single(engine.ValidateElements([wall, beam], pairs));
        Assert.Equal("R04", issue.RuleId);
        Assert.Equal(wall.Guid, issue.ElementGuid);
        Assert.Equal(beam.Guid, issue.RelatedGuid);
        Assert.Equal($"El elemento se superpone con {beam.Guid} sin unión de geometría.", issue.Message);
        Assert.Equal("join_geometry", issue.Rule.Fix.Type);
    }

    [Fact]
    public void No_overlap_ignores_joined_pairs_and_wrong_categories()
    {
        var engine = CreateEngine();
        var wall = Valid();
        var beam = Valid("OST_StructuralFraming", "VIG_CA_25x50_FC210", "Ss_20_10_20");
        var column = Valid("OST_StructuralColumns", "COL_CA_40x40_FC210", "Ss_20_10_10");

        Assert.Empty(engine.ValidateElements([wall, beam], [new OverlapPair(wall.Guid, beam.Guid, AreJoined: true)]));
        Assert.Empty(engine.ValidateElements([wall, column], [new OverlapPair(wall.Guid, column.Guid, AreJoined: false)]));
    }

    [Fact]
    public void No_overlap_reports_joined_pairs_when_ignore_if_joined_is_false()
    {
        var engine = CreateEngine(root =>
        {
            foreach (var r in root["rules"]!.AsArray())
            {
                if ((string?)r!["id"] == "R04")
                {
                    r["params"]!["ignore_if_joined"] = false;
                }
            }
        });
        var wall = Valid();
        var beam = Valid("OST_StructuralFraming", "VIG_CA_25x50_FC210", "Ss_20_10_20");
        Assert.Single(engine.ValidateOverlaps([wall, beam], [new OverlapPair(wall.Guid, beam.Guid, AreJoined: true)]));
    }

    // ---- required_parameters (R05) ----

    [Fact]
    public void Required_parameters_flags_each_missing_loin_parameter()
    {
        var engine = CreateEngine();
        var column = Valid("OST_StructuralColumns", "COL_CA_40x40_FC210", "Ss_20_10_10");
        column.Parameters["BIM_Material"] = null;
        column.Parameters.Remove("BIM_Resistencia_fc");

        var issues = Run(engine, column);
        Assert.Equal(2, issues.Count);
        Assert.All(issues, i => Assert.Equal("R05", i.RuleId));
        Assert.Equal(["BIM_Material", "BIM_Resistencia_fc"], issues.Select(i => i.Parameter!).ToArray());
        Assert.Equal("Falta el parámetro \"BIM_Resistencia_fc\" exigido por el LOIN.", issues[1].Message);
    }

    [Fact]
    public void Required_parameters_only_applies_to_listed_categories()
    {
        var engine = CreateEngine();
        var wall = Valid();
        wall.Parameters.Remove("BIM_Resistencia_fc"); // muros solo piden BIM_Material
        Assert.Empty(Run(engine, wall));

        var door = Valid("OST_Doors", "PTA_MAD_090x210", "Ss_25_30_20");
        door.Parameters.Clear(); // puertas fuera del scope de R05
        Assert.Empty(Run(engine, door));
    }

    // ---- level_required (R07) ----

    [Fact]
    public void Level_required_flags_element_without_level()
    {
        var engine = CreateEngine();
        var beam = Valid("OST_StructuralFraming", "VIG_CA_25x50_FC210", "Ss_20_10_20");
        beam.Level = null;
        var issue = Assert.Single(Run(engine, beam));
        Assert.Equal("R07", issue.RuleId);
        Assert.Equal("El elemento no está asociado a un nivel.", issue.Message);
    }

    [Fact]
    public void Level_required_not_applied_to_doors()
    {
        var engine = CreateEngine();
        var door = Valid("OST_Doors", "PTA_MAD_090x210", "Ss_25_30_20");
        door.Level = null;
        Assert.Empty(Run(engine, door));
    }

    // ---- file_naming (R06) ----

    [Theory]
    [InlineData("HKT-EQP-ZZ-ZZ-M3-S-0001")]
    [InlineData("HKT-EQP-ZZ-ZZ-M3-S-0001.rvt")]
    [InlineData("PRY01-ARQ-01-N1-M3-A-0042")]
    public void File_naming_accepts_iso19650_names(string fileName)
    {
        Assert.Empty(CreateEngine().ValidateDocument(fileName));
    }

    [Theory]
    [InlineData("Proyecto1")]
    [InlineData("hkt-eqp-zz-zz-m3-s-0001")]
    [InlineData("HKT-EQP-ZZ-ZZ-M2-S-0001")]
    public void File_naming_flags_other_names(string fileName)
    {
        var issue = Assert.Single(CreateEngine().ValidateDocument(fileName));
        Assert.Equal("R06", issue.RuleId);
        Assert.Null(issue.ElementGuid);
        Assert.Contains($"\"{RuleEngine.StripExtension(fileName)}\"", issue.Message);
        Assert.DoesNotContain("{file_name}", issue.Message);
    }

    // ---- generales ----

    [Fact]
    public void Disabled_rules_are_not_evaluated()
    {
        var engine = CreateEngine(root =>
        {
            foreach (var r in root["rules"]!.AsArray())
            {
                r!["enabled"] = false;
            }
        });
        var bad = Valid(typeName: "Genérico", code: null);
        bad.Level = null;
        Assert.Empty(Run(engine, bad));
        Assert.Empty(engine.ValidateDocument("x"));
    }

    [Fact]
    public void Several_rules_can_fire_on_the_same_element()
    {
        var engine = CreateEngine();
        var bad = Valid("OST_StructuralFraming", "Genérico", null);
        bad.Level = null;
        bad.Parameters.Clear();
        var ids = Run(engine, bad).Select(i => i.RuleId).ToList();
        Assert.Equal(["R01", "R02", "R05", "R05", "R07"], ids.Order().ToArray());
    }

    [Fact]
    public void Issue_keys_are_unique_per_parameter_and_pair()
    {
        var engine = CreateEngine();
        var column = Valid("OST_StructuralColumns", "COL_CA_40x40_FC210", "Ss_20_10_10");
        column.Parameters.Clear();
        var keys = Run(engine, column).Select(i => i.Key).ToList();
        Assert.Equal(keys.Count, keys.Distinct().Count());
    }
}
