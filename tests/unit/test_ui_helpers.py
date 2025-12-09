from pathlib import Path
import utils.ui_helpers as ui_helpers

def test_load_css_file_reads_content(tmp_path):
    p = tmp_path / "style.css"
    p.write_text("body{color:red}", encoding="utf-8")
    s = ui_helpers.load_css_file(str(p))
    assert s == "body{color:red}"

def test_inject_custom_css_calls_markdown(monkeypatch):
    calls = []
    def fake_markdown(s, unsafe_allow_html=False):
        calls.append((s, unsafe_allow_html))
    monkeypatch.setattr(ui_helpers.st, "markdown", fake_markdown)
    ui_helpers.inject_custom_css("a{b:c}")
    assert calls and "a{b:c}" in calls[0][0]

def test_inject_custom_css_skips_empty(monkeypatch):
    calls = []
    def fake_markdown(s, unsafe_allow_html=False):
        calls.append(1)
    monkeypatch.setattr(ui_helpers.st, "markdown", fake_markdown)
    ui_helpers.inject_custom_css("")
    assert calls == []

def test_inject_custom_js_calls_markdown(monkeypatch):
    calls = []
    def fake_markdown(s, unsafe_allow_html=False):
        calls.append((s, unsafe_allow_html))
    monkeypatch.setattr(ui_helpers.st, "markdown", fake_markdown)
    ui_helpers.inject_custom_js("console.log('x')")
    assert calls and "console.log('x')" in calls[0][0]

def test_inject_custom_js_skips_empty(monkeypatch):
    calls = []
    def fake_markdown(s, unsafe_allow_html=False):
        calls.append(1)
    monkeypatch.setattr(ui_helpers.st, "markdown", fake_markdown)
    ui_helpers.inject_custom_js("")
    assert calls == []

