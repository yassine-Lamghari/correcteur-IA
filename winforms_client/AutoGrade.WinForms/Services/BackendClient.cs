using System.Net.Http.Json;
using AutoGrade.WinForms.Models;

namespace AutoGrade.WinForms.Services;

public sealed class BackendClient
{
    private readonly HttpClient _httpClient;

    public BackendClient(string baseUrl)
    {
        _httpClient = new HttpClient { BaseAddress = new Uri(baseUrl) };
    }

    public async Task<OcrResponse?> OcrAsync(string imageBase64, string task)
    {
        var payload = new { image_base64 = imageBase64, task };
        var response = await _httpClient.PostAsJsonAsync("/api/v1/ocr", payload);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<OcrResponse>();
    }

    public async Task<GradeResponse?> GradeAsync(QuestionSpec question, string studentAnswer)
    {
        var payload = new { question, student_answer = studentAnswer };
        var response = await _httpClient.PostAsJsonAsync("/api/v1/grade", payload);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<GradeResponse>();
    }

    public async Task<FeedbackResponse?> FeedbackAsync(QuestionSpec question, string studentAnswer, GradeResponse grade)
    {
        var payload = new { question, student_answer = studentAnswer, grade };
        var response = await _httpClient.PostAsJsonAsync("/api/v1/feedback", payload);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<FeedbackResponse>();
    }

    public async Task<TranslateResponse?> TranslateAsync(string text, string sourceLang, string targetLang)
    {
        var payload = new { text, source_lang = sourceLang, target_lang = targetLang };
        var response = await _httpClient.PostAsJsonAsync("/api/v1/translate", payload);
        response.EnsureSuccessStatusCode();
        return await response.Content.ReadFromJsonAsync<TranslateResponse>();
    }
}
