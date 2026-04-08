using AutoGrade.WinForms.Models;
using AutoGrade.WinForms.Services;

namespace AutoGrade.WinForms;

public sealed class MainForm : Form
{
    private readonly BackendClient _client = new("http://127.0.0.1:8000");
    private readonly TextBox _answerBox = new() { Width = 760 };
    private readonly TextBox _logBox = new() { Multiline = true, ScrollBars = ScrollBars.Vertical, Width = 760, Height = 320 };
    private readonly ComboBox _taskBox = new() { Width = 110, DropDownStyle = ComboBoxStyle.DropDownList };
    private readonly ComboBox _targetLangBox = new() { Width = 80, DropDownStyle = ComboBoxStyle.DropDownList };

    private string _imageBase64 = string.Empty;
    private GradeResponse? _lastGrade;
    private string _lastFeedback = string.Empty;

    public MainForm()
    {
        Text = "AutoGrade OCR - WinForms";
        Width = 820;
        Height = 600;

        _taskBox.Items.AddRange(["Text", "Formula", "Table"]);
        _taskBox.SelectedIndex = 0;

        _targetLangBox.Items.AddRange(["en", "fr", "es", "ar"]);
        _targetLangBox.SelectedIndex = 0;

        var buttonSelect = new Button { Text = "Select Scan", Width = 100 };
        var buttonOcr = new Button { Text = "Run OCR", Width = 100 };
        var buttonGrade = new Button { Text = "Grade", Width = 100 };
        var buttonFeedback = new Button { Text = "Feedback", Width = 100 };
        var buttonTranslate = new Button { Text = "Translate", Width = 100 };

        buttonSelect.Click += OnSelectScan;
        buttonOcr.Click += async (_, _) => await OnRunOcr();
        buttonGrade.Click += async (_, _) => await OnGrade();
        buttonFeedback.Click += async (_, _) => await OnFeedback();
        buttonTranslate.Click += async (_, _) => await OnTranslate();

        var topRow = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 40, AutoSize = false };
        topRow.Controls.AddRange([buttonSelect, _taskBox, buttonOcr, buttonGrade, buttonFeedback, _targetLangBox, buttonTranslate]);

        var midRow = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 44 };
        midRow.Controls.Add(new Label { Text = "Student answer", Width = 100, TextAlign = ContentAlignment.MiddleLeft });
        midRow.Controls.Add(_answerBox);

        var bottomRow = new Panel { Dock = DockStyle.Fill };
        _logBox.Dock = DockStyle.Fill;
        bottomRow.Controls.Add(_logBox);

        Controls.Add(bottomRow);
        Controls.Add(midRow);
        Controls.Add(topRow);
    }

    private void OnSelectScan(object? sender, EventArgs e)
    {
        using var dialog = new OpenFileDialog();
        dialog.Filter = "Image files|*.png;*.jpg;*.jpeg;*.webp";
        if (dialog.ShowDialog() != DialogResult.OK)
        {
            return;
        }

        _imageBase64 = Convert.ToBase64String(File.ReadAllBytes(dialog.FileName));
        Log($"Loaded file: {dialog.FileName}");
    }

    private async Task OnRunOcr()
    {
        if (string.IsNullOrWhiteSpace(_imageBase64))
        {
            MessageBox.Show("Select an image before OCR.", "Missing file", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        try
        {
            var result = await _client.OcrAsync(_imageBase64, _taskBox.Text);
            if (result is null) return;

            Log($"OCR raw text:{Environment.NewLine}{result.raw_text}");
            if (result.extracted_answers.Count > 0)
            {
                _answerBox.Text = result.extracted_answers[0];
                Log($"First extracted answer prefilled: {result.extracted_answers[0]}");
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "OCR error", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private async Task OnGrade()
    {
        var question = new QuestionSpec(
            question_id: "q1",
            type: "short_answer",
            prompt: "Explain photosynthesis",
            max_points: 5,
            expected_answer: string.Empty,
            keywords: ["photosynthesis", "chlorophyll", "light", "energy"]
        );

        try
        {
            _lastGrade = await _client.GradeAsync(question, _answerBox.Text);
            if (_lastGrade is not null)
            {
                Log($"Grade result: {_lastGrade}");
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "Grading error", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private async Task OnFeedback()
    {
        if (_lastGrade is null)
        {
            MessageBox.Show("Run grading first.", "Missing grade", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        var question = new QuestionSpec(
            question_id: "q1",
            type: "short_answer",
            prompt: "Explain photosynthesis",
            max_points: 5,
            expected_answer: string.Empty,
            keywords: ["photosynthesis", "chlorophyll", "light", "energy"]
        );

        try
        {
            var result = await _client.FeedbackAsync(question, _answerBox.Text, _lastGrade);
            if (result is null) return;

            _lastFeedback = result.feedback;
            Log($"Feedback: {_lastFeedback}");
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "Feedback error", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private async Task OnTranslate()
    {
        if (string.IsNullOrWhiteSpace(_lastFeedback))
        {
            MessageBox.Show("Generate feedback first.", "Missing feedback", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        try
        {
            var result = await _client.TranslateAsync(_lastFeedback, "en", _targetLangBox.Text);
            if (result is null) return;

            Log($"Translated feedback: {result.translated_text}");
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "Translation error", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void Log(string text)
    {
        _logBox.AppendText(text + Environment.NewLine + Environment.NewLine);
    }
}
