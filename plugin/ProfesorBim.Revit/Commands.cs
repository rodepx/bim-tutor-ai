using System;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace ProfesorBim.Revit;

[Transaction(TransactionMode.Manual)]
public sealed class TogglePanelCommand : IExternalCommand
{
    public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
    {
        try
        {
            var pane = commandData.Application.GetDockablePane(App.PaneId);
            if (pane.IsShown())
            {
                pane.Hide();
            }
            else
            {
                pane.Show();
            }
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            message = "No se pudo abrir el panel: " + ex.Message;
            return Result.Failed;
        }
    }
}

[Transaction(TransactionMode.Manual)]
public sealed class ValidateAllCommand : IExternalCommand
{
    public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
    {
        var doc = commandData.Application.ActiveUIDocument?.Document;
        if (doc is null || doc.IsFamilyDocument)
        {
            message = "Abre un modelo de proyecto (no de familia).";
            return Result.Failed;
        }
        var app = App.Instance;
        try
        {
            app.Live.Reset();
            app.Session.ValidateAll(doc);
            app.Panel.SetStatus($"Validación completa: {app.Session.Elements.Count} elementos, {app.Session.Issues.Count} issues.");
            ShowPane(commandData.Application);
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            message = "Error al validar: " + ex.Message;
            return Result.Failed;
        }
    }

    internal static void ShowPane(UIApplication uiapp)
    {
        try
        {
            var pane = uiapp.GetDockablePane(App.PaneId);
            if (!pane.IsShown())
            {
                pane.Show();
            }
        }
        catch (Exception)
        {
            // El panel es opcional para el comando.
        }
    }
}

[Transaction(TransactionMode.Manual)]
public sealed class SendToBackendCommand : IExternalCommand
{
    public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
    {
        var doc = commandData.Application.ActiveUIDocument?.Document;
        if (doc is null || doc.IsFamilyDocument)
        {
            message = "Abre un modelo de proyecto (no de familia).";
            return Result.Failed;
        }
        var app = App.Instance;
        try
        {
            // Lectura en el hilo de Revit; el envío HTTP va a un hilo de fondo (no bloquea).
            app.Live.Reset();
            app.Session.ValidateAll(doc);
            var snapshot = app.Session.BuildSnapshot(app.SelectedCdeState);
            ValidateAllCommand.ShowPane(commandData.Application);
            _ = app.Sync.SendSnapshotAsync(snapshot);
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            message = "Error al preparar el snapshot: " + ex.Message;
            return Result.Failed;
        }
    }
}
