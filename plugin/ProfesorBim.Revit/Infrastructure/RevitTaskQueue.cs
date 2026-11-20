using System;
using System.Collections.Concurrent;
using System.Threading.Tasks;
using Autodesk.Revit.UI;

namespace ProfesorBim.Revit.Infrastructure;

/// <summary>
/// Ejecuta trabajo en el contexto válido de la API de Revit desde la UI no modal (WPF) vía un único ExternalEvent.
/// Toda modificación del modelo pasa por aquí (dentro de una Transaction en el delegado).
/// </summary>
public sealed class RevitTaskQueue : IExternalEventHandler
{
    private readonly ConcurrentQueue<(Action<UIApplication> Run, Action<Exception> Fail)> _queue = new();
    private ExternalEvent? _event;

    private RevitTaskQueue()
    {
    }

    /// <summary>Debe llamarse en contexto de API (OnStartup o un comando).</summary>
    public static RevitTaskQueue Create()
    {
        var handler = new RevitTaskQueue();
        handler._event = ExternalEvent.Create(handler);
        return handler;
    }

    public Task<T> RunAsync<T>(Func<UIApplication, T> work)
    {
        var tcs = new TaskCompletionSource<T>(TaskCreationOptions.RunContinuationsAsynchronously);
        _queue.Enqueue((
            app =>
            {
                try
                {
                    tcs.TrySetResult(work(app));
                }
                catch (Exception ex)
                {
                    tcs.TrySetException(ex);
                }
            },
            ex => tcs.TrySetException(ex)));

        var request = _event?.Raise() ?? ExternalEventRequest.Denied;
        if (request is ExternalEventRequest.Denied or ExternalEventRequest.TimedOut)
        {
            // No se ejecuta nada tarde: se cancela todo lo encolado y se avisa a quien espera.
            var error = new InvalidOperationException("Revit rechazó la operación (¿hay un comando o diálogo activo?). Inténtalo de nuevo.");
            while (_queue.TryDequeue(out var item))
            {
                item.Fail(error);
            }
        }
        return tcs.Task;
    }

    public Task RunAsync(Action<UIApplication> work) => RunAsync<bool>(app =>
    {
        work(app);
        return true;
    });

    public void Execute(UIApplication app)
    {
        while (_queue.TryDequeue(out var item))
        {
            item.Run(app);
        }
    }

    public string GetName() => "Profesor BIM - cola de tareas";
}
