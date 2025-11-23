import streamlit as st
import app_modern


def test_apply_theme_injects_light_css(monkeypatch):
    calls = []

    def fake_markdown(text, unsafe_allow_html=False):
        calls.append(text)

    monkeypatch.setattr(st, "markdown", fake_markdown)
    app_modern.apply_theme()
    combined = " ".join(calls)
    assert "ai-real-estate-theme','light'" in combined
    assert ".stTextInput" in combined and "margin-bottom: 0.75rem" in combined
    assert "div[data-baseweb=\"modal\"]" in combined
    assert "[data-testid=\"stFileUploadDropzone\"]" in combined and "margin-bottom: 0.75rem" in combined