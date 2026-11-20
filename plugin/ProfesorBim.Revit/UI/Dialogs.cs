using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using ProfesorBim.Core.Api;

namespace ProfesorBim.Revit.UI;

/// <summary>Diálogos pequeños construidos en código (texto libre, lista, microencuesta).</summary>
internal static class Dialogs
{
    public static string? AskText(FrameworkElement owner, string title, string prompt, string? initial)
    {
        var box = new TextBox { Text = initial ?? "", MinWidth = 320, Margin = new Thickness(0, 6, 0, 0) };
        box.SelectAll();
        var ok = Show(owner, title, prompt, box, () => !string.IsNullOrWhiteSpace(box.Text), box);
        return ok ? box.Text.Trim() : null;
    }

    public sealed record PickItem(string Value, string Display)
    {
        public override string ToString() => Display;
    }

    public static string? Pick(FrameworkElement owner, string title, string prompt, IReadOnlyList<PickItem> items, string? preselect)
    {
        if (items.Count == 0)
        {
            MessageBox.Show("No hay códigos de la tabla Uniclass para esta categoría.", title, MessageBoxButton.OK, MessageBoxImage.Information);
            return null;
        }
        var combo = new ComboBox { ItemsSource = items, MinWidth = 360, Margin = new Thickness(0, 6, 0, 0) };
        combo.SelectedItem = items.FirstOrDefault(i => i.Value == preselect) ?? items[0];
        var ok = Show(owner, title, prompt, combo, () => combo.SelectedItem is PickItem, combo);
        return ok ? (combo.SelectedItem as PickItem)?.Value : null;
    }

    /// <summary>Microencuesta "No pude, ¿por qué?". Devuelve (reason, comment) o null si se cancela.</summary>
    public static (string Reason, string? Comment)? AskFeedback(FrameworkElement owner, string ruleTitle)
    {
        var panel = new StackPanel();
        var radios = new List<RadioButton>();
        foreach (var (value, label) in FeedbackReasons.All)
        {
            var rb = new RadioButton { Content = label, Tag = value, GroupName = "reason", Margin = new Thickness(0, 3, 0, 0) };
            radios.Add(rb);
            panel.Children.Add(rb);
        }
        radios[0].IsChecked = true;
        panel.Children.Add(new TextBlock { Text = "Comentario (opcional, máx. 500 caracteres):", Margin = new Thickness(0, 8, 0, 0) });
        var comment = new TextBox
        {
            MaxLength = 500,
            AcceptsReturn = true,
            TextWrapping = TextWrapping.Wrap,
            Height = 70,
            MinWidth = 320,
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
        };
        panel.Children.Add(comment);

        var ok = Show(owner, "No pude, ¿por qué?", $"Cuéntanos por qué no pudiste corregir: {ruleTitle}", panel, () => radios.Any(r => r.IsChecked == true), radios[0]);
        if (!ok)
        {
            return null;
        }
        var reason = (string)radios.First(r => r.IsChecked == true).Tag;
        return (reason, string.IsNullOrWhiteSpace(comment.Text) ? null : comment.Text.Trim());
    }

    private static bool Show(FrameworkElement owner, string title, string prompt, UIElement content, System.Func<bool> canAccept, UIElement focus)
    {
        var window = new Window
        {
            Title = title,
            SizeToContent = SizeToContent.WidthAndHeight,
            ResizeMode = ResizeMode.NoResize,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
            ShowInTaskbar = false,
            MaxWidth = 560,
        };
        var root = new StackPanel { Margin = new Thickness(12) };
        root.Children.Add(new TextBlock { Text = prompt, TextWrapping = TextWrapping.Wrap, MaxWidth = 520 });
        root.Children.Add(content);
        var buttons = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right, Margin = new Thickness(0, 12, 0, 0) };
        var okButton = new Button { Content = "Aceptar", IsDefault = true, MinWidth = 80, Margin = new Thickness(0, 0, 6, 0) };
        var cancelButton = new Button { Content = "Cancelar", IsCancel = true, MinWidth = 80 };
        okButton.Click += (_, _) =>
        {
            if (canAccept())
            {
                window.DialogResult = true;
            }
        };
        buttons.Children.Add(okButton);
        buttons.Children.Add(cancelButton);
        root.Children.Add(buttons);
        window.Content = root;
        window.Loaded += (_, _) => focus.Focus();

        var ownerWindow = Window.GetWindow(owner);
        if (ownerWindow is { IsVisible: true })
        {
            window.Owner = ownerWindow;
        }
        else
        {
            new WindowInteropHelper(window).Owner = Process.GetCurrentProcess().MainWindowHandle;
        }
        return window.ShowDialog() == true;
    }
}
