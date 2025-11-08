"""
UI Helper Functions for Enhanced Styling and Dark Mode
Provides utilities for injecting custom CSS and JavaScript into Streamlit apps
"""

import streamlit as st
from pathlib import Path
from typing import Optional


def load_css_file(file_path: str) -> str:
    """
    Load CSS file content

    Args:
        file_path: Path to the CSS file

    Returns:
        CSS content as string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        st.warning(f"Could not load CSS file {file_path}: {e}")
        return ""


def load_js_file(file_path: str) -> str:
    """
    Load JavaScript file content

    Args:
        file_path: Path to the JS file

    Returns:
        JavaScript content as string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        st.warning(f"Could not load JS file {file_path}: {e}")
        return ""


def inject_custom_css(css_content: str):
    """
    Inject custom CSS into the Streamlit app

    Args:
        css_content: CSS content to inject
    """
    if css_content:
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)


def inject_custom_js(js_content: str):
    """
    Inject custom JavaScript into the Streamlit app

    Args:
        js_content: JavaScript content to inject
    """
    if js_content:
        st.markdown(f'<script>{js_content}</script>', unsafe_allow_html=True)


def load_and_inject_styles():
    """
    Load and inject all custom styles (CSS and JS) for the app
    This includes dark mode styles, Tailwind CSS, and theme toggle functionality
    """
    # Get base directory
    base_dir = Path(__file__).parent.parent
    assets_dir = base_dir / 'assets'
    css_dir = assets_dir / 'css'
    js_dir = assets_dir / 'js'

    # Load dark mode CSS
    dark_mode_css_path = css_dir / 'dark_mode.css'
    if dark_mode_css_path.exists():
        dark_mode_css = load_css_file(str(dark_mode_css_path))
        inject_custom_css(dark_mode_css)

    # Load Tailwind custom CSS
    tailwind_css_path = css_dir / 'tailwind_custom.css'
    if tailwind_css_path.exists():
        tailwind_css = load_css_file(str(tailwind_css_path))
        inject_custom_css(tailwind_css)

    # Load dark mode JavaScript
    dark_mode_js_path = js_dir / 'dark_mode.js'
    if dark_mode_js_path.exists():
        dark_mode_js = load_js_file(str(dark_mode_js_path))
        inject_custom_js(dark_mode_js)


def inject_enhanced_form_styles():
    """
    Inject enhanced styles specifically for form elements
    to ensure proper visibility in both light and dark modes
    """
    enhanced_css = """
    <style>
    /* Enhanced form label visibility */
    .stTextInput > label,
    .stTextArea > label,
    .stSelectbox > label,
    .stMultiSelect > label,
    .stNumberInput > label,
    .stDateInput > label,
    .stTimeInput > label,
    .stFileUploader > label {
        color: var(--text-primary) !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        margin-bottom: 0.5rem !important;
        display: block !important;
    }

    /* Specific enhancement for "Your Email Address" and similar labels */
    .stTextInput label[data-testid="stWidgetLabel"],
    label:contains("Email"),
    label:contains("email") {
        color: #fafafa !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
    }

    /* Enhanced input field visibility */
    input[type="text"],
    input[type="email"],
    input[type="password"],
    input[type="number"],
    textarea,
    select {
        background-color: var(--input-background) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--input-border) !important;
        padding: 0.625rem 0.875rem !important;
        border-radius: 0.375rem !important;
    }

    /* Focus states */
    input:focus,
    textarea:focus,
    select:focus {
        border-color: var(--input-focus) !important;
        box-shadow: 0 0 0 3px rgba(74, 158, 255, 0.1) !important;
        outline: none !important;
    }

    /* Placeholder text */
    input::placeholder,
    textarea::placeholder {
        color: var(--text-tertiary) !important;
        opacity: 0.7 !important;
    }

    /* Help text */
    .stTextInput > div > div > p,
    .stTextArea > div > div > p {
        color: var(--text-secondary) !important;
        font-size: 0.875rem !important;
    }
    </style>
    """
    st.markdown(enhanced_css, unsafe_allow_html=True)


def create_metric_card(label: str, value: str, delta: Optional[str] = None,
                       delta_color: str = "normal") -> None:
    """
    Create a styled metric card with proper dark mode support

    Args:
        label: Metric label
        value: Metric value
        delta: Optional delta value
        delta_color: Color for delta ("normal", "inverse", "off")
    """
    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color
    )


def create_info_box(title: str, content: str, box_type: str = "info"):
    """
    Create a styled information box with proper dark mode support

    Args:
        title: Box title
        content: Box content
        box_type: Type of box ("info", "success", "warning", "error")
    """
    icon_map = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌"
    }

    icon = icon_map.get(box_type, "ℹ️")

    box_html = f"""
    <div class="alert alert-{box_type}" style="
        padding: 1rem;
        border-radius: 0.375rem;
        margin-bottom: 1rem;
        border-left: 4px solid var(--{box_type}-color);
        background-color: rgba(var(--{box_type}-color-rgb), 0.1);
    ">
        <div style="display: flex; align-items: start; gap: 0.75rem;">
            <span style="font-size: 1.5rem;">{icon}</span>
            <div>
                <h4 style="margin: 0 0 0.5rem 0; color: var(--text-primary); font-weight: 600;">
                    {title}
                </h4>
                <p style="margin: 0; color: var(--text-secondary);">
                    {content}
                </p>
            </div>
        </div>
    </div>
    """
    st.markdown(box_html, unsafe_allow_html=True)


def create_card(title: str, content: str, footer: Optional[str] = None):
    """
    Create a styled card component with proper dark mode support

    Args:
        title: Card title
        content: Card content
        footer: Optional footer content
    """
    footer_html = f'<div class="card-footer" style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color); color: var(--text-secondary); font-size: 0.875rem;">{footer}</div>' if footer else ''

    card_html = f"""
    <div class="card" style="
        background-color: var(--background-secondary);
        border: 1px solid var(--border-color);
        border-radius: 0.5rem;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: var(--shadow-sm);
    ">
        <h3 class="card-header" style="margin: 0 0 1rem 0; color: var(--text-primary); font-weight: 600; font-size: 1.25rem;">
            {title}
        </h3>
        <div class="card-body" style="color: var(--text-secondary);">
            {content}
        </div>
        {footer_html}
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)


def add_vertical_space(lines: int = 1):
    """
    Add vertical spacing

    Args:
        lines: Number of lines of vertical space
    """
    for _ in range(lines):
        st.markdown("<br>", unsafe_allow_html=True)


def create_badge(text: str, badge_type: str = "primary") -> str:
    """
    Create a badge HTML element

    Args:
        text: Badge text
        badge_type: Type of badge ("primary", "success", "warning", "danger")

    Returns:
        HTML string for the badge
    """
    return f'<span class="badge badge-{badge_type}" style="display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 500;">{text}</span>'


def inject_tailwind_cdn():
    """
    Inject Tailwind CSS CDN link
    Note: For production, it's recommended to use a build process instead of CDN
    """
    tailwind_cdn = """
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        primary: '#4a9eff',
                        'bg-primary': '#0e1117',
                        'bg-secondary': '#1a1d24',
                    }
                }
            }
        }
    </script>
    """
    st.markdown(tailwind_cdn, unsafe_allow_html=True)
