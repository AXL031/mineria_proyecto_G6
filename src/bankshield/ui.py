"""Estilo compartido: emojis monocromáticos de Google Noto servidos localmente."""

import base64
from html import escape
from functools import lru_cache
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parents[2] / "dashboard/assets/noto-emoji"
PAGE_ICONS = {
    "🛡": "shield", "💳": "credit", "🌐": "networks",
    "📈": "forecast", "🗣": "complaints", "🧩": "segments",
}


@lru_cache(maxsize=1)
def _emoji_css() -> str:
    encoded = base64.b64encode((ASSETS / "NotoEmoji-Demo.ttf").read_bytes()).decode("ascii")
    return f"""
    <style>
    @font-face {{
        font-family: 'BankShield Noto Emoji';
        src: url(data:font/ttf;base64,{encoded}) format('truetype');
        font-style: normal;
        font-weight: 100 900;
        font-display: block;
        unicode-range: U+200D, U+2139, U+2600-27BF, U+FE0E-FE0F, U+1F000-1FAFF;
    }}
    [data-testid='stAppViewContainer'] p,
    [data-testid='stAppViewContainer'] h1,
    [data-testid='stAppViewContainer'] h2,
    [data-testid='stAppViewContainer'] h3,
    [data-testid='stAppViewContainer'] li,
    [data-testid='stAppViewContainer'] label,
    [data-testid='stAppViewContainer'] button,
    [data-testid='stAppViewContainer'] [role='tab'],
    .main-title, .module-header, .badge-sim, .compliance-box {{
        font-family: 'BankShield Noto Emoji', 'Source Sans', 'Source Sans Pro', sans-serif !important;
        font-variant-emoji: text;
    }}
    </style>
    """


def configure_page(*, page_title: str, page_icon: str = "🛡️", **kwargs) -> None:
    """Usa el mismo diseño Google en texto y favicon, sin servicios externos."""
    icon_name = PAGE_ICONS[page_icon.replace("\ufe0f", "").replace("\ufe0e", "")]
    st.set_page_config(page_title=page_title, page_icon=str(ASSETS / f"{icon_name}.png"), **kwargs)
    st.markdown(_emoji_css(), unsafe_allow_html=True)
    st.markdown(_semantic_css(st.context.theme.type == "dark"), unsafe_allow_html=True)


def _semantic_css(dark: bool) -> str:
    warning, danger, success, info = (
        ("#facc15", "#f87171", "#4ade80", "#60a5fa") if dark else
        ("#854d0e", "#b91c1c", "#166534", "#1d4ed8")
    )
    return f"""
    <style>
    :root {{ --bs-warning: {warning}; --bs-danger: {danger};
             --bs-success: {success}; --bs-info: {info}; }}
    .bs-notice {{
        border: 1px solid color-mix(in srgb, var(--bs-state) 32%, transparent);
        border-left: 4px solid var(--bs-state);
        border-radius: 10px;
        background: color-mix(in srgb, var(--bs-state) 8%, transparent);
        padding: 1rem 1.1rem;
        margin: 0.8rem 0 1.1rem;
    }}
    .bs-notice[data-state='warning'] {{ --bs-state: var(--bs-warning); }}
    .bs-notice[data-state='danger'] {{ --bs-state: var(--bs-danger); }}
    .bs-notice[data-state='success'] {{ --bs-state: var(--bs-success); }}
    .bs-notice[data-state='info'] {{ --bs-state: var(--bs-info); }}
    .bs-notice-title {{ color: var(--bs-state); font-weight: 650; display: flex; gap: 0.6rem; align-items: center; }}
    .bs-notice-detail {{ margin-top: 0.35rem; line-height: 1.5; }}
    .bs-notice-icon {{ font-family: 'BankShield Noto Emoji', sans-serif; font-size: 1.15rem; }}
    button[kind='primary'] {{ background-color: #2563eb !important; border-color: #2563eb !important; color: white !important; }}
    button:focus-visible, [role='tab']:focus-visible {{ outline: 2px solid var(--bs-info) !important; outline-offset: 3px; }}
    .st-key-graph-tabs [role='tablist'] {{ gap: 0.5rem; }}
    .st-key-graph-tabs .react-aria-SelectionIndicator {{ background-color: var(--bs-info) !important; }}
    .st-key-graph-tabs [role='tab'][aria-selected='true'] {{ color: var(--bs-info) !important; }}
    .st-key-graph-tabs [role='tab'][data-key='1'] .stMarkdownColoredText {{ color: var(--bs-warning) !important; }}
    </style>
    """


def status_notice(state: str, title: str, detail: str) -> None:
    """Estado identificado por icono, texto y color; mantiene legibilidad en ambos temas."""
    icons = {"warning": "⚠", "danger": "⚠", "success": "🛡", "info": "ℹ"}
    icon = icons[state]
    st.markdown(
        f'<div class="bs-notice" data-state="{state}" role="status">'
        f'<div class="bs-notice-title"><span class="bs-notice-icon" aria-hidden="true">{icon}</span>{escape(title)}</div>'
        f'<div class="bs-notice-detail">{escape(detail)}</div></div>',
        unsafe_allow_html=True,
    )
