using Autodesk.Revit.UI;

namespace ProfesorBim.Revit.UI;

internal sealed class IssuesPaneProvider : IDockablePaneProvider
{
    private readonly IssuesPanel _panel;

    public IssuesPaneProvider(IssuesPanel panel) => _panel = panel;

    public void SetupDockablePane(DockablePaneProviderData data)
    {
        data.FrameworkElement = _panel;
        data.InitialState = new DockablePaneState
        {
            DockPosition = DockPosition.Right,
        };
        data.VisibleByDefault = true;
    }
}
