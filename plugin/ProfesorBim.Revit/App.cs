using System;
using System.IO;
using System.Reflection;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;
using ProfesorBim.Core.Api;
using ProfesorBim.Core.Config;
using ProfesorBim.Core.Rules;
using ProfesorBim.Revit.Infrastructure;
using ProfesorBim.Revit.Model;
using ProfesorBim.Revit.UI;

namespace ProfesorBim.Revit;

/// <summary>Punto de entrada del add-in: ribbon, panel acoplable, validación en vivo.</summary>
public sealed class App : IExternalApplication
{
    public const string TabName = "Profesor BIM";
    public static readonly DockablePaneId PaneId = new(new Guid("FA6E7758-503D-43D2-A987-28BFA7E15439"));

    private static App? _instance;

    public static App Instance => _instance ?? throw new InvalidOperationException("Profesor BIM no se inició.");

    public string AssemblyDir { get; private set; } = "";
    public PluginSettings Settings { get; private set; } = new();
    public RuleEngine Engine { get; private set; } = null!;
    public ValidationSession Session { get; private set; } = null!;
    public LiveValidation Live { get; private set; } = null!;
    public RevitTaskQueue Queue { get; private set; } = null!;
    public BackendClient Backend { get; private set; } = null!;
    public BackendSync Sync { get; private set; } = null!;
    public IssuesPanel Panel { get; private set; } = null!;

    /// <summary>Error al cargar rules.json / uniclass (se muestra en el panel; se valida con reglas vacías).</summary>
    public string? LoadError { get; private set; }

    /// <summary>Estado CDE elegido en el combo del panel (lo usa también el botón del ribbon).</summary>
    public string SelectedCdeState { get; set; } = CdeStates.Wip;

    public Result OnStartup(UIControlledApplication application)
    {
        _instance = this;
        AssemblyDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? Environment.CurrentDirectory;
        Settings = PluginSettings.LoadOrDefault(AssemblyDir);
        Engine = LoadEngine();
        Session = new ValidationSession(Engine);
        Live = new LiveValidation(Session, TimeSpan.FromMilliseconds(Math.Max(100, Settings.LiveValidationDebounceMs)), Settings.LiveValidation);
        Backend = new BackendClient(Settings.BaseUrl, TimeSpan.FromSeconds(Math.Max(1, Settings.TimeoutSeconds)));
        Queue = RevitTaskQueue.Create();

        Panel = new IssuesPanel(this);
        Sync = new BackendSync(Backend, Session, Panel);
        application.RegisterDockablePane(PaneId, "Profesor BIM", new IssuesPaneProvider(Panel));

        CreateRibbon(application);

        Session.IssuesChanged += Panel.RefreshIssues;
        Live.Failed += Panel.SetStatus;
        application.ControlledApplication.DocumentChanged += Live.OnDocumentChanged;
        application.ControlledApplication.DocumentClosing += OnDocumentClosing;
        application.ControlledApplication.DocumentSavedAs += OnDocumentSavedAs;
        application.Idling += Live.OnIdling;
        application.ViewActivated += OnViewActivated;

        if (LoadError is not null)
        {
            Panel.SetStatus(LoadError);
        }
        return Result.Succeeded;
    }

    public Result OnShutdown(UIControlledApplication application)
    {
        application.ControlledApplication.DocumentChanged -= Live.OnDocumentChanged;
        application.ControlledApplication.DocumentClosing -= OnDocumentClosing;
        application.ControlledApplication.DocumentSavedAs -= OnDocumentSavedAs;
        application.Idling -= Live.OnIdling;
        application.ViewActivated -= OnViewActivated;
        return Result.Succeeded;
    }

    private RuleEngine LoadEngine()
    {
        var rulesPath = Settings.ResolvePath(AssemblyDir, Settings.RulesPath);
        try
        {
            var rules = RuleSetLoader.Load(rulesPath);
            var uniclassPath = RuleSetLoader.ResolveUniclassPath(rules, rulesPath, AssemblyDir, Settings.UniclassPath);
            UniclassTable table;
            try
            {
                table = UniclassTable.Load(uniclassPath);
            }
            catch (Exception ex)
            {
                LoadError = $"No se pudo leer la tabla Uniclass ({uniclassPath}): {ex.Message}";
                table = new UniclassTable([]);
            }
            return new RuleEngine(rules, table);
        }
        catch (Exception ex)
        {
            LoadError = $"No se pudo cargar rules.json ({rulesPath}): {ex.Message}";
            return new RuleEngine(new RuleSet(), new UniclassTable([]));
        }
    }

    private void CreateRibbon(UIControlledApplication application)
    {
        try
        {
            application.CreateRibbonTab(TabName);
        }
        catch (Autodesk.Revit.Exceptions.ArgumentException)
        {
            // La pestaña ya existe.
        }
        var ribbonPanel = application.CreateRibbonPanel(TabName, "Validación BEP");
        var asm = Assembly.GetExecutingAssembly().Location;

        AddButton(ribbonPanel, "ProfesorBim_Panel", "Panel", asm, typeof(TogglePanelCommand).FullName!,
            "Muestra u oculta el panel de issues de Profesor BIM.", "P", System.Windows.Media.Color.FromRgb(0x1E, 0x6F, 0xB8));
        AddButton(ribbonPanel, "ProfesorBim_ValidateAll", "Validar todo", asm, typeof(ValidateAllCommand).FullName!,
            "Valida todo el modelo contra las reglas del BEP (data/rules.json).", "V", System.Windows.Media.Color.FromRgb(0x2E, 0x8B, 0x57));
        AddButton(ribbonPanel, "ProfesorBim_Send", "Enviar al backend", asm, typeof(SendToBackendCommand).FullName!,
            "Envía un snapshot (elementos + issues) al backend con el estado CDE elegido en el panel.", "E", System.Windows.Media.Color.FromRgb(0xC0, 0x6C, 0x00));
    }

    private static void AddButton(RibbonPanel panel, string name, string text, string asm, string className, string tooltip, string letter, System.Windows.Media.Color color)
    {
        var data = new PushButtonData(name, text, asm, className)
        {
            ToolTip = tooltip,
            LargeImage = Icons.Make(letter, color, 32),
            Image = Icons.Make(letter, color, 16),
        };
        panel.AddItem(data);
    }

    private void OnViewActivated(object? sender, ViewActivatedEventArgs e)
    {
        var doc = e.Document;
        if (doc is null || doc.IsFamilyDocument || Session.IsCurrent(doc))
        {
            return;
        }
        try
        {
            Live.Reset();
            Session.ValidateAll(doc);
        }
        catch (Exception ex)
        {
            Panel.SetStatus("No se pudo validar el documento: " + ex.Message);
        }
    }

    private void OnDocumentClosing(object? sender, DocumentClosingEventArgs e)
    {
        if (e.Document is { } doc && Session.IsCurrent(doc))
        {
            Live.Reset();
            Session.Clear();
        }
    }

    private void OnDocumentSavedAs(object? sender, DocumentSavedAsEventArgs e)
    {
        if (e.Document is { IsFamilyDocument: false } doc)
        {
            try
            {
                Live.Reset();
                Session.ValidateAll(doc);
            }
            catch (Exception ex)
            {
                Panel.SetStatus("No se pudo revalidar tras Guardar como: " + ex.Message);
            }
        }
    }
}
