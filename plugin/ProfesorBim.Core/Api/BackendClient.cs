using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization.Metadata;
using ProfesorBim.Core.Model;

namespace ProfesorBim.Core.Api;

/// <summary>Resultado de una llamada al backend: nunca lanza excepción hacia la UI.</summary>
public sealed record ApiResult<T>(bool Ok, T? Value, string? Error, int? StatusCode = null)
{
    public static ApiResult<T> Success(T value, int status) => new(true, value, null, status);

    public static ApiResult<T> Fail(string error, int? status = null) => new(false, default, error, status);
}

/// <summary>
/// Cliente HTTP del backend (contracts/openapi.yaml). Un único HttpClient por proceso,
/// todo async con timeout. Llamar SIEMPRE fuera del hilo de la API de Revit o con await (no .Result).
/// </summary>
public sealed class BackendClient
{
    private static readonly HttpClient SharedHttp = new(new SocketsHttpHandler
    {
        PooledConnectionLifetime = TimeSpan.FromMinutes(5),
        ConnectTimeout = TimeSpan.FromSeconds(3),
    })
    {
        // El timeout real se aplica por petición con CancellationTokenSource.
        Timeout = Timeout.InfiniteTimeSpan,
    };

    private readonly HttpClient _http;
    private readonly string _baseUrl;
    private readonly TimeSpan _timeout;

    public BackendClient(string baseUrl, TimeSpan timeout, HttpClient? http = null)
    {
        _http = http ?? SharedHttp;
        _baseUrl = baseUrl.TrimEnd('/');
        _timeout = timeout;
    }

    public string BaseUrl => _baseUrl;

    public Task<ApiResult<HealthResponse>> HealthAsync(CancellationToken ct = default) =>
        SendAsync(HttpMethod.Get, "/health", null, ProfesorBimJsonContext.Default.HealthResponse, ct);

    public Task<ApiResult<Snapshot>> CreateSnapshotAsync(SnapshotCreate snapshot, CancellationToken ct = default) =>
        SendAsync(HttpMethod.Post, "/snapshots", JsonContent.Create(snapshot, ProfesorBimJsonContext.Default.SnapshotCreate), ProfesorBimJsonContext.Default.Snapshot, ct, longTimeout: true);

    public Task<ApiResult<List<Issue>>> ListIssuesAsync(int snapshotId, string? status = IssueStatuses.Open, CancellationToken ct = default)
    {
        var path = $"/issues?snapshot_id={snapshotId}" + (status is null ? "" : $"&status={Uri.EscapeDataString(status)}");
        return SendAsync(HttpMethod.Get, path, null, ProfesorBimJsonContext.Default.ListIssue, ct);
    }

    public Task<ApiResult<Issue>> UpdateIssueAsync(int issueId, string status, string? fixedBy, CancellationToken ct = default) =>
        SendAsync(HttpMethod.Patch, $"/issues/{issueId}", JsonContent.Create(new IssueUpdate { Status = status, FixedBy = fixedBy }, ProfesorBimJsonContext.Default.IssueUpdate), ProfesorBimJsonContext.Default.Issue, ct);

    public Task<ApiResult<Feedback>> CreateFeedbackAsync(FeedbackCreate feedback, CancellationToken ct = default) =>
        SendAsync(HttpMethod.Post, "/feedback", JsonContent.Create(feedback, ProfesorBimJsonContext.Default.FeedbackCreate), ProfesorBimJsonContext.Default.Feedback, ct);

    public Task<ApiResult<Explanation>> ExplainAsync(string ruleId, ElementData? element, CancellationToken ct = default) =>
        SendAsync(HttpMethod.Post, "/ai/explain", JsonContent.Create(new ExplainRequest { RuleId = ruleId, Element = element }, ProfesorBimJsonContext.Default.ExplainRequest), ProfesorBimJsonContext.Default.Explanation, ct, longTimeout: true);

    public Task<ApiResult<ClassificationSuggestion>> SuggestClassificationAsync(ElementData element, CancellationToken ct = default) =>
        SendAsync(HttpMethod.Post, "/ai/suggest-classification", JsonContent.Create(new SuggestClassificationRequest { Element = element }, ProfesorBimJsonContext.Default.SuggestClassificationRequest), ProfesorBimJsonContext.Default.ClassificationSuggestion, ct, longTimeout: true);

    public static string Serialize(SnapshotCreate snapshot) => JsonSerializer.Serialize(snapshot, ProfesorBimJsonContext.Default.SnapshotCreate);

    private async Task<ApiResult<T>> SendAsync<T>(HttpMethod method, string path, HttpContent? content, JsonTypeInfo<T> typeInfo, CancellationToken ct, bool longTimeout = false)
    {
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        // Las llamadas de IA y snapshots grandes pueden tardar más.
        cts.CancelAfter(longTimeout ? _timeout * 3 : _timeout);
        try
        {
            using var request = new HttpRequestMessage(method, _baseUrl + path) { Content = content };
            using var response = await _http.SendAsync(request, HttpCompletionOption.ResponseContentRead, cts.Token).ConfigureAwait(false);
            var status = (int)response.StatusCode;
            var body = await response.Content.ReadAsStringAsync(cts.Token).ConfigureAwait(false);
            if (!response.IsSuccessStatusCode)
            {
                return ApiResult<T>.Fail($"HTTP {status}: {ExtractDetail(body)}", status);
            }
            var value = JsonSerializer.Deserialize(body, typeInfo);
            return value is null ? ApiResult<T>.Fail("Respuesta vacía del backend.", status) : ApiResult<T>.Success(value, status);
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            return ApiResult<T>.Fail($"Tiempo de espera agotado ({_baseUrl}).");
        }
        catch (HttpRequestException ex)
        {
            return ApiResult<T>.Fail($"Backend no disponible ({_baseUrl}): {ex.Message}");
        }
        catch (JsonException ex)
        {
            return ApiResult<T>.Fail($"Respuesta inválida del backend: {ex.Message}");
        }
        catch (Exception ex)
        {
            return ApiResult<T>.Fail($"Error inesperado: {ex.Message}");
        }
    }

    private static string ExtractDetail(string body)
    {
        try
        {
            var err = JsonSerializer.Deserialize(body, ProfesorBimJsonContext.Default.ErrorResponse);
            if (!string.IsNullOrWhiteSpace(err?.Detail))
            {
                return err.Detail;
            }
        }
        catch (JsonException)
        {
            // FastAPI 422 devuelve detail como lista; se muestra el cuerpo recortado.
        }
        return body.Length > 300 ? body[..300] : body;
    }
}
