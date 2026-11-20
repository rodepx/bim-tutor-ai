using System.Globalization;
using System.Windows;
using System.Windows.Media;
using System.Windows.Media.Imaging;

namespace ProfesorBim.Revit.UI;

/// <summary>Iconos simples del ribbon dibujados en memoria (sin archivos de imagen).</summary>
internal static class Icons
{
    public static BitmapSource Make(string letter, Color color, int size)
    {
        var visual = new DrawingVisual();
        using (var dc = visual.RenderOpen())
        {
            var brush = new SolidColorBrush(color);
            brush.Freeze();
            dc.DrawRoundedRectangle(brush, null, new Rect(0, 0, size, size), size / 5.0, size / 5.0);
            var text = new FormattedText(letter, CultureInfo.InvariantCulture, FlowDirection.LeftToRight,
                new Typeface(new FontFamily("Segoe UI"), FontStyles.Normal, FontWeights.Bold, FontStretches.Normal),
                size * 0.62, Brushes.White, 1.0);
            dc.DrawText(text, new Point((size - text.Width) / 2, (size - text.Height) / 2));
        }
        var bmp = new RenderTargetBitmap(size, size, 96, 96, PixelFormats.Pbgra32);
        bmp.Render(visual);
        bmp.Freeze();
        return bmp;
    }
}
