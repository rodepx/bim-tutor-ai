using System.Text.Json;
using ProfesorBim.Core.Api;
using ProfesorBim.Core.Config;
using ProfesorBim.Core.Model;
using ProfesorBim.Core.Rules;

namespace ProfesorBim.Tests;

/// <summary>JSON snake_case según contracts/openapi.yaml.</summary>
public class ContractTests
{
    private static ValidationIssue FakeIssue(string? guid) => new()
    {
        Rule = new Rule { Id = "R02", Severity = "error" },
        Message = "m",
        ElementGuid = guid,
    };

    [Fact]
    public void Snapshot_serializes_with_openapi_field_names()
    {
        var element = new ElementData
        {
            Guid = "abc-123",
            ElementId = 42,
            Category = "OST_Walls",
            Discipline = "ARQ",
            FamilyName = "Muro básico",
            TypeName = "MUR_CA_e25_FC210",
            ClassificationCode = "Ss_25_10_20",
            Level = "Nivel 1",
            VolumeM3 = 1.25,
            AreaM2 = 5,
            LengthM = 2,
            TypeElementId = 7,
            ClassificationParameterFound = "Uniclass_Codigo",
        };
        element.Parameters["BIM_Material"] = "Concreto";
        element.Parameters["BIM_Resistencia_fc"] = null;

        var snap = SnapshotFactory.Create("HKT-EQP-ZZ-ZZ-M3-S-0001.rvt", CdeStates.Shared, "0.1.0", "ana", [element], [FakeIssue("abc-123"), FakeIssue(null)], new DateTime(2026, 11, 19, 8, 5, 0));
        using var doc = JsonDocument.Parse(BackendClient.Serialize(snap));
        var root = doc.RootElement;

        Assert.Equal("HKT", root.GetProperty("project_code").GetString());
        Assert.Equal("HKT-EQP-ZZ-ZZ-M3-S-0001", root.GetProperty("file_name").GetString());
        Assert.Equal("20261119-0805", root.GetProperty("version_label").GetString());
        Assert.Equal("SHARED", root.GetProperty("cde_state").GetString());
        Assert.Equal("0.1.0", root.GetProperty("rules_version").GetString());
        Assert.Equal("ana", root.GetProperty("author").GetString());

        var el = root.GetProperty("elements")[0];
        foreach (var name in new[] { "guid", "element_id", "category", "discipline", "family_name", "type_name", "classification_code", "level", "volume_m3", "area_m2", "length_m", "parameters" })
        {
            Assert.True(el.TryGetProperty(name, out _), $"falta {name}");
        }
        Assert.False(el.TryGetProperty("type_element_id", out _));
        Assert.False(el.TryGetProperty("classification_parameter_found", out _));
        Assert.Equal("Concreto", el.GetProperty("parameters").GetProperty("BIM_Material").GetString());
        Assert.Equal(JsonValueKind.Null, el.GetProperty("parameters").GetProperty("BIM_Resistencia_fc").ValueKind);

        var issues = root.GetProperty("issues");
        Assert.Equal("abc-123", issues[0].GetProperty("element_guid").GetString());
        Assert.Equal("R02", issues[0].GetProperty("rule_id").GetString());
        Assert.Equal("error", issues[0].GetProperty("severity").GetString());
        Assert.Equal(JsonValueKind.Null, issues[1].GetProperty("element_guid").ValueKind);
    }

    [Theory]
    [InlineData("HKT-EQP-ZZ-ZZ-M3-S-0001", "HKT")]
    [InlineData("PRY01-ARQ-01-N1-M3-A-0042.rvt", "PRY01")]
    [InlineData("Proyecto1", "HKT")]
    [InlineData("ab-x", "HKT")]
    public void Project_code_comes_from_first_segment(string fileName, string expected)
    {
        Assert.Equal(expected, SnapshotFactory.ProjectCodeFrom(fileName));
    }

    [Fact]
    public void Feedback_reasons_match_openapi_enum()
    {
        Assert.Equal(
            ["no_entiendo_regla", "no_encuentro_codigo", "falta_informacion", "regla_no_aplica", "error_del_plugin", "otro"],
            FeedbackReasons.All.Select(r => r.Key).ToArray());
        var json = JsonSerializer.Serialize(new FeedbackCreate { ElementGuid = "g", RuleId = "R01", Reason = "otro" }, ProfesorBimJsonContext.Default.FeedbackCreate);
        Assert.Contains("\"element_guid\":\"g\"", json);
        Assert.Contains("\"issue_id\":null", json);
        // Regla de documento (R06): element_guid se envía como null explícito (campo requerido, contrato 0.2.0)
        var doc = JsonSerializer.Serialize(new FeedbackCreate { RuleId = "R06" }, ProfesorBimJsonContext.Default.FeedbackCreate);
        Assert.Contains("\"element_guid\":null", doc);
    }

    [Fact]
    public void Issue_update_and_suggestion_round_trip()
    {
        var patch = JsonSerializer.Serialize(new IssueUpdate { Status = "fixed", FixedBy = "one_click" }, ProfesorBimJsonContext.Default.IssueUpdate);
        Assert.Equal("{\"status\":\"fixed\",\"fixed_by\":\"one_click\"}", patch);

        var s = JsonSerializer.Deserialize("""
            {"element_guid":"g","candidates":[{"code":"Ss_25_10_20","title_es":"Muros","table":"Ss","revit_categories":["OST_Walls"]}],
             "suggested_code":"Ss_25_10_20","reason":"es de concreto","mode":"mock"}
            """, ProfesorBimJsonContext.Default.ClassificationSuggestion)!;
        Assert.Equal("Ss_25_10_20", s.SuggestedCode);
        Assert.Equal("OST_Walls", s.Candidates[0].RevitCategories[0]);
    }

    [Fact]
    public void Settings_default_and_parse()
    {
        var dir = Path.Combine(Path.GetTempPath(), "pbim-" + Guid.NewGuid());
        Directory.CreateDirectory(dir);
        try
        {
            Assert.Equal("http://localhost:8000/api", PluginSettings.LoadOrDefault(dir).BaseUrl);
            File.WriteAllText(Path.Combine(dir, PluginSettings.FileName), """{ "base_url": "http://10.0.0.5:9000/api", "timeout_seconds": 3 }""");
            var s = PluginSettings.LoadOrDefault(dir);
            Assert.Equal("http://10.0.0.5:9000/api", s.BaseUrl);
            Assert.Equal(3, s.TimeoutSeconds);
            Assert.Equal("data/rules.json", s.RulesPath);
        }
        finally
        {
            Directory.Delete(dir, true);
        }
    }

    [Fact]
    public async Task Backend_client_reports_offline_without_throwing()
    {
        // Puerto 9 (discard) en localhost: conexión rechazada rápidamente.
        var client = new BackendClient("http://127.0.0.1:9/api", TimeSpan.FromSeconds(2));
        var result = await client.HealthAsync();
        Assert.False(result.Ok);
        Assert.False(string.IsNullOrWhiteSpace(result.Error));
    }
}
