"""Design system compartido del panel: "Estilo Material AI".

Toda página llama a :func:`configure_page`, que inyecta las variables y los
componentes del design system (ver ``docs/diseno-ui.md``).  No se descargan
fuentes ni bibliotecas: la tipografía usa la pila ``Roboto, Arial,
sans-serif`` y los iconos son SVG en línea (estilo Lucide) o los iconos
Material que Streamlit ya incluye (``:material/nombre:``).  No se usan emojis.
"""

from __future__ import annotations

from collections.abc import Iterable
from html import escape

import streamlit as st

# Iconos de página (favicon y menú lateral): iconos Material incluidos en Streamlit.
PAGE_ICONS = {
    "🛡": ":material/shield:",
    "💳": ":material/credit_card:",
    "🌐": ":material/hub:",
    "📈": ":material/trending_up:",
    "🗣": ":material/forum:",
    "🧩": ":material/category:",
}

# Trazos SVG estilo Lucide (24x24, sin relleno).
ICONS = {
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
    "credit-card": '<rect width="20" height="14" x="2" y="5" rx="2"/><line x1="2" x2="22" y1="10" y2="10"/>',
    "network": '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" x2="15.42" y1="13.51" y2="17.49"/><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"/>',
    "trending-up": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "message": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    "line-chart": '<path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "compass": '<circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>',
    "sparkles": '<path d="M12 3l1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2z"/><path d="M19 3v4"/><path d="M21 5h-4"/>',
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>',
    "scale": '<path d="M12 3v18"/><path d="M5 7h14"/><path d="m5 7-3 7a3 3 0 0 0 6 0z"/><path d="m19 7-3 7a3 3 0 0 0 6 0z"/>',
    "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
}

NOTICE_ICONS = {"warning": "alert", "danger": "alert", "success": "check", "info": "info"}


def icon(name: str, size: int = 20, label: str | None = None) -> str:
    """SVG en línea de :data:`ICONS`; decorativo salvo que se indique ``label``."""
    paths = ICONS[name]
    aria = f'role="img" aria-label="{escape(label)}"' if label else 'aria-hidden="true"'
    return (
        f'<svg class="bs-icon" {aria} width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round">{paths}</svg>'
    )


def configure_page(*, page_title: str, page_icon: str = "🛡", **kwargs) -> None:
    """Configura la página e inyecta el design system Material AI."""
    key = page_icon.replace("️", "").replace("︎", "")
    st.set_page_config(page_title=page_title, page_icon=PAGE_ICONS.get(key, key), **kwargs)
    st.markdown(design_css(st.context.theme.type == "dark"), unsafe_allow_html=True)


def design_css(dark: bool = False) -> str:
    """Hoja de estilos del design system; ``dark`` ajusta superficies y texto."""
    surface, surface_alt, text, muted, stroke, tint = (
        ("#1F2023", "#2A2B2F", "#E8EAED", "#9AA0A6", "#3C4043", "0.16") if dark else
        ("#FFFFFF", "#F8F9FA", "#3C4043", "#5F6368", "#E3E6EA", "0.08")
    )
    return f"""
<style>
:root {{
  --brand-blue: #4285F4; --brand-red: #EA4335; --brand-yellow: #FBBC05;
  --brand-green: #34A853; --brand-cyan: #00BCD4;
  --white: #FFFFFF; --light-grey: #F8F9FA; --dark-grey: #3C4043;
  --font-sans: Roboto, Arial, sans-serif;
  --font-mono: 'JetBrains Mono', Consolas, monospace;
  --shadow-material: 0 2px 4px rgba(0,0,0,0.1);
  --shadow-raised: 0 2px 12px rgba(0,0,0,0.06), 0 6px 16px rgba(60,64,67,0.12);
  --radius-sm: 8px; --radius-md: 16px; --radius-lg: 24px;
  --surface: {surface}; --surface-alt: {surface_alt}; --text: {text};
  --muted: {muted}; --stroke: {stroke}; --tint: {tint};
  --gradient-brand: linear-gradient(to right, #4285F4, #34A853);
  --gradient-ai: linear-gradient(90deg, #4285F4, #EA4335, #FBBC05, #34A853, #4285F4);
  --ease: cubic-bezier(0.2, 0, 0, 1);
  --bs-warning: {"#FDD663" if dark else "#B06000"}; --bs-danger: {"#F28B82" if dark else "#C5221F"};
  --bs-success: {"#81C995" if dark else "#137333"}; --bs-info: {"#8AB4F8" if dark else "#1A73E8"};
}}

/* Base */
html, body, [data-testid='stAppViewContainer'], [data-testid='stSidebar'] {{
  font-family: var(--font-sans); color: var(--text);
}}
[data-testid='stAppViewContainer'] .block-container {{ max-width: 1280px; padding: 2.5rem 1.5rem 4rem; }}
/* La barra superior queda transparente (solo el menú) y la franja de marca
   va al inicio del contenido: se desplaza con la página y no tapa nada. */
[data-testid='stHeader'] {{ background: transparent; }}
[data-testid='stMain']::before {{
  content: ''; display: block; flex: none; height: 3px; width: 100%;
  background-image: var(--gradient-ai); background-size: 200% 100%; pointer-events: none;
}}
code, pre {{ font-family: var(--font-mono); }}
p, li {{ line-height: 1.6; }}

/* Títulos: st.title recibe la barra de marca */
[data-testid='stHeading'] h1 {{ font-weight: 700; letter-spacing: -0.02em; font-size: 2.25rem; }}
[data-testid='stMain'] [data-testid='stHeading'] h1::after {{
  content: ''; display: block; width: 64px; height: 4px; margin-top: 0.6rem;
  border-radius: 2px; background-image: var(--gradient-brand);
}}
[data-testid='stHeading'] h2, [data-testid='stHeading'] h3 {{ font-weight: 600; letter-spacing: -0.01em; }}
[data-testid='stCaptionContainer'] {{ color: var(--muted); }}

/* Tarjetas: métricas, formularios, expanders, tablas */
[data-testid='stMetric'], [data-testid='stForm'], [data-testid='stExpander'] details,
.bs-card {{
  background: var(--surface); border: 1px solid var(--stroke);
  border-radius: var(--radius-sm); box-shadow: var(--shadow-material);
  transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out, border-color 0.3s ease-in-out;
}}
[data-testid='stMetric'] {{ padding: 1rem 1.1rem; border-top: 3px solid var(--brand-blue); }}
[data-testid='stMetric']:hover, .bs-card:hover {{ transform: translateY(-2px); box-shadow: var(--shadow-raised); }}
[data-testid='stColumn']:nth-child(4n+2) [data-testid='stMetric'] {{ border-top-color: var(--brand-green); }}
[data-testid='stColumn']:nth-child(4n+3) [data-testid='stMetric'] {{ border-top-color: var(--brand-yellow); }}
[data-testid='stColumn']:nth-child(4n+4) [data-testid='stMetric'] {{ border-top-color: var(--brand-red); }}
[data-testid='stMetricLabel'] {{ color: var(--muted); font-size: 0.875rem; font-weight: 500; letter-spacing: 0.01em; }}
[data-testid='stMetricValue'] {{ font-weight: 700; }}
[data-testid='stForm'] {{ padding: 1.25rem; }}
[data-testid='stExpander'] details summary {{ font-weight: 500; }}
[data-testid='stDataFrame'], [data-testid='stTable'] {{
  border-radius: var(--radius-sm); box-shadow: var(--shadow-material); overflow: hidden;
}}

/* Avisos de Streamlit (st.info, st.warning, st.error, st.success) */
[data-testid='stAlertContainer'] {{
  border-radius: var(--radius-sm); box-shadow: var(--shadow-material);
  border-left: 4px solid var(--bs-info);
}}
[data-testid='stAlertContainer']:has([data-testid='stAlertContentWarning']) {{ border-left-color: var(--brand-yellow); }}
[data-testid='stAlertContainer']:has([data-testid='stAlertContentError']) {{ border-left-color: var(--brand-red); }}
[data-testid='stAlertContainer']:has([data-testid='stAlertContentSuccess']) {{ border-left-color: var(--brand-green); }}

/* Pestañas */
[role='tablist'] {{ gap: 0.35rem; border-bottom: 1px solid var(--stroke); }}
[role='tab'] {{
  border-radius: var(--radius-sm) var(--radius-sm) 0 0; padding: 0.55rem 0.95rem;
  font-weight: 500; cursor: pointer;
  transition: background-color 0.3s ease-in-out, color 0.3s ease-in-out;
}}
[role='tab']:hover {{ background: rgba(66, 133, 244, var(--tint)); color: var(--brand-blue); }}
[role='tab'][aria-selected='true'] {{ color: var(--brand-blue) !important; }}
.react-aria-SelectionIndicator, [data-baseweb='tab-highlight'] {{ background-color: var(--brand-blue) !important; height: 3px; border-radius: 3px 3px 0 0; }}

/* Botones con ripple Material */
.stButton button, .stFormSubmitButton button, .stDownloadButton button, .material-ripple-effect {{
  position: relative; overflow: hidden; cursor: pointer;
  border-radius: var(--radius-sm); font-weight: 600;
  transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out,
              background-color 0.3s ease-in-out, border-color 0.3s ease-in-out, color 0.3s ease-in-out;
}}
.stButton button:hover, .stFormSubmitButton button:hover, .stDownloadButton button:hover,
.material-ripple-effect:hover {{ box-shadow: var(--shadow-raised); transform: translateY(-1px); }}
.stButton button:active, .stFormSubmitButton button:active, .stDownloadButton button:active,
.material-ripple-effect:active {{ transform: translateY(1px); }}
.stButton button::after, .stFormSubmitButton button::after, .stDownloadButton button::after,
.material-ripple-effect::after {{
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(circle, rgba(255,255,255,0.45) 10%, transparent 10.01%) center / 1000% 1000% no-repeat;
  opacity: 0; transition: background-size 0.5s ease-out, opacity 0.8s ease-out;
}}
.stButton button:active::after, .stFormSubmitButton button:active::after,
.stDownloadButton button:active::after, .material-ripple-effect:active::after {{
  background-size: 0 0; opacity: 1; transition: 0s;
}}
button[kind='primary'], button[kind='primaryFormSubmit'] {{
  background-color: var(--brand-blue) !important; border-color: var(--brand-blue) !important; color: var(--white) !important;
}}
button[kind='primary']:hover, button[kind='primaryFormSubmit']:hover {{
  background-color: #3367D6 !important; border-color: #3367D6 !important;
}}
button:focus-visible, [role='tab']:focus-visible, a:focus-visible {{
  outline: 2px solid var(--brand-blue) !important; outline-offset: 2px;
}}

/* Campos */
[data-baseweb='input'], [data-baseweb='select'] > div, [data-baseweb='textarea'] {{
  border-radius: var(--radius-sm) !important; transition: box-shadow 0.3s ease-in-out;
}}
[data-baseweb='input']:focus-within, [data-baseweb='select'] > div:focus-within, [data-baseweb='textarea']:focus-within {{
  box-shadow: 0 0 0 2px var(--surface), 0 0 0 4px var(--brand-blue);
}}

/* Menú lateral */
[data-testid='stSidebar'] {{ background: var(--surface-alt); border-right: 1px solid var(--stroke); }}
[data-testid='stSidebarNav'] a {{
  border-radius: var(--radius-sm); cursor: pointer;
  transition: background-color 0.3s ease-in-out, color 0.3s ease-in-out;
}}
[data-testid='stSidebarNav'] a:hover {{ background: rgba(66, 133, 244, var(--tint)); }}
[data-testid='stSidebarNav'] a[aria-current='page'] {{
  background: rgba(66, 133, 244, calc(var(--tint) * 1.6)); box-shadow: inset 3px 0 0 var(--brand-blue);
}}
[data-testid='stSidebarNav'] a[aria-current='page'] span {{ color: var(--brand-blue); font-weight: 500; }}

/* Navegación por secciones (st.navigation) */
[data-testid='stSidebarHeader'] {{ padding-bottom: 0.5rem; }}
[data-testid='stSidebarHeader'] img {{ height: 2.25rem; max-width: 100%; }}
[data-testid='stNavSectionHeader'] {{
  color: var(--muted); font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em;
  text-transform: uppercase; margin: 1rem 0 0.25rem; padding-left: 0.5rem;
}}
[data-testid='stSidebarNavLink'] {{ padding: 0.45rem 0.6rem; margin: 1px 0; }}
[data-testid='stSidebarNavLink'] span {{ font-size: 0.95rem; }}
[data-testid='stSidebarNavLink'] [data-testid='stIconMaterial'] {{ color: var(--muted); }}
[data-testid='stSidebarNavLink'][aria-current='page'] [data-testid='stIconMaterial'] {{ color: var(--brand-blue); }}
[data-testid='stSidebarNavSeparator'] {{ border-color: var(--stroke); }}

/* Barra superior: indicador de ejecución como barra de carga, sin "Stop" */
[data-testid='stToolbar'] {{ right: 1rem; }}
[data-testid='stStatusWidget'] {{ visibility: hidden; position: relative; min-width: 140px; }}
[data-testid='stStatusWidget']::after {{
  content: ''; visibility: visible; position: absolute; right: 0; top: 50%;
  width: 120px; height: 4px; margin-top: -2px; border-radius: 4px;
  background-image: var(--gradient-ai); background-size: 300% 100%;
  animation: bs-shimmer 1.6s linear infinite;
}}
[data-testid='stMainMenu'] button, [data-testid='stToolbarActionButton'] button {{
  border-radius: var(--radius-sm); transition: background-color 0.3s ease-in-out;
}}
[data-testid='stMainMenu'] button:hover {{ background: rgba(66, 133, 244, var(--tint)); }}

/* Carga de IA: barra degradada en lugar de spinner circular */
.ai-loading-animation {{
  height: 4px; border-radius: 4px; background-image: var(--gradient-ai);
  background-size: 300% 100%; animation: bs-shimmer 1.6s linear infinite;
}}
[data-testid='stSpinner'] [data-testid='stSpinnerIcon'], [data-testid='stSpinner'] i {{ display: none; }}
[data-testid='stSpinner']::before {{
  content: ''; display: block; width: 180px; height: 4px; margin-bottom: 0.5rem; border-radius: 4px;
  background-image: var(--gradient-ai); background-size: 300% 100%; animation: bs-shimmer 1.6s linear infinite;
}}
@keyframes bs-shimmer {{ from {{ background-position: 0% 0; }} to {{ background-position: 150% 0; }} }}

/* Cabecera tipo hero con ilustración abstracta de datos */
.bs-hero {{
  position: relative; display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr);
  gap: 1.5rem; align-items: center; padding: 2rem 2.25rem; margin: 0 0 1.75rem;
  border-radius: var(--radius-md); border: 1px solid var(--stroke); box-shadow: var(--shadow-material);
  background:
    radial-gradient(120% 140% at 100% 0%, rgba(66,133,244,var(--tint)) 0%, transparent 55%),
    radial-gradient(90% 120% at 0% 100%, rgba(52,168,83,var(--tint)) 0%, transparent 60%),
    var(--surface);
  animation: bs-enter 420ms var(--ease) both;
}}
.bs-hero-eyebrow {{
  display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.8rem; font-weight: 500;
  letter-spacing: 0.06em; text-transform: uppercase; color: var(--brand-blue);
}}
.bs-hero h1.bs-hero-title {{
  font-size: clamp(1.9rem, 3.6vw, 2.75rem); font-weight: 700; line-height: 1.15; letter-spacing: -0.02em;
  margin: 0.4rem 0 0.6rem; padding: 0; color: var(--text);
}}
.bs-hero-title .bs-gradient-text {{
  background-image: var(--gradient-brand); -webkit-background-clip: text; background-clip: text; color: transparent;
}}
.bs-hero-sub {{ font-size: 1.05rem; color: var(--muted); max-width: 62ch; margin: 0 0 1rem; }}
.bs-hero-visual {{ justify-self: end; width: 100%; max-width: 300px; }}
.bs-hero-visual svg {{ width: 100%; height: auto; display: block; }}
.bs-float {{ animation: bs-float 6s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }}
.bs-float.d1 {{ animation-delay: -1.5s; }} .bs-float.d2 {{ animation-delay: -3s; }} .bs-float.d3 {{ animation-delay: -4.5s; }}
@keyframes bs-float {{ 0%, 100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-8px); }} }}
@keyframes bs-enter {{ from {{ opacity: 0; transform: translateY(16px); }} to {{ opacity: 1; transform: translateY(0); }} }}

/* Chips */
.bs-chips {{ display: flex; flex-wrap: wrap; gap: 0.5rem; }}
.bs-chip {{
  display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.3rem 0.75rem;
  border-radius: 999px; font-size: 0.8rem; font-weight: 500;
  background: rgba(66,133,244,var(--tint)); color: var(--brand-blue); border: 1px solid rgba(66,133,244,0.25);
}}
.bs-chip[data-tone='green'] {{ background: rgba(52,168,83,var(--tint)); color: var(--bs-success); border-color: rgba(52,168,83,0.3); }}
.bs-chip[data-tone='yellow'] {{ background: rgba(251,188,5,var(--tint)); color: var(--bs-warning); border-color: rgba(251,188,5,0.35); }}
.bs-chip[data-tone='red'] {{ background: rgba(234,67,53,var(--tint)); color: var(--bs-danger); border-color: rgba(234,67,53,0.3); }}
.bs-icon {{ flex: none; vertical-align: -0.2em; }}

/* Tarjetas de módulo (portada) */
.bs-module-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }}
.bs-module {{ display: flex; gap: 1rem; padding: 1.15rem 1.25rem; animation: bs-enter 420ms var(--ease) both; }}
.bs-module:nth-child(2) {{ animation-delay: 80ms; }} .bs-module:nth-child(3) {{ animation-delay: 160ms; }}
.bs-module:nth-child(4) {{ animation-delay: 240ms; }} .bs-module:nth-child(5) {{ animation-delay: 320ms; }}
.bs-module:nth-child(6) {{ animation-delay: 400ms; }} .bs-module:nth-child(7) {{ animation-delay: 480ms; }}
.bs-module-icon {{
  flex: none; width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center;
  color: var(--white); background: var(--brand-blue); box-shadow: var(--shadow-material);
}}
.bs-module[data-tone='green'] .bs-module-icon {{ background: var(--brand-green); }}
.bs-module[data-tone='yellow'] .bs-module-icon {{ background: var(--brand-yellow); color: var(--dark-grey); }}
.bs-module[data-tone='red'] .bs-module-icon {{ background: var(--brand-red); }}
.bs-module[data-tone='cyan'] .bs-module-icon {{ background: var(--brand-cyan); }}
.bs-module h4 {{ margin: 0 0 0.25rem; padding: 0; font-size: 1.02rem; font-weight: 600; color: var(--text); }}
.bs-module p {{ margin: 0; color: var(--muted); font-size: 0.92rem; }}

/* Avisos propios */
.bs-notice {{
  border: 1px solid var(--stroke); border-left: 4px solid var(--bs-state);
  border-radius: var(--radius-sm); background: var(--surface); box-shadow: var(--shadow-material);
  padding: 0.95rem 1.1rem; margin: 0.8rem 0 1.1rem;
}}
.bs-notice[data-state='warning'] {{ --bs-state: var(--brand-yellow); --bs-state-text: var(--bs-warning); }}
.bs-notice[data-state='danger'] {{ --bs-state: var(--brand-red); --bs-state-text: var(--bs-danger); }}
.bs-notice[data-state='success'] {{ --bs-state: var(--brand-green); --bs-state-text: var(--bs-success); }}
.bs-notice[data-state='info'] {{ --bs-state: var(--brand-blue); --bs-state-text: var(--bs-info); }}
.bs-notice-title {{ color: var(--bs-state-text); font-weight: 600; display: flex; gap: 0.55rem; align-items: center; }}
.bs-notice-detail {{ margin-top: 0.35rem; line-height: 1.5; }}

@media (max-width: 768px) {{
  .bs-hero {{ grid-template-columns: 1fr; padding: 1.5rem; }}
  .bs-hero-visual {{ justify-self: start; max-width: 220px; }}
  .bs-module-grid {{ grid-template-columns: 1fr; }}
}}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation: none !important; transition: none !important; }}
}}
</style>
"""


def _hero_visual() -> str:
    """Ilustración abstracta de una red de datos con nodos flotantes."""
    return """
<svg viewBox="0 0 280 200" role="img" aria-label="Ilustración abstracta de una red de datos">
  <defs>
    <linearGradient id="bs-g1" x1="0" x2="1"><stop offset="0" stop-color="#4285F4"/><stop offset="1" stop-color="#34A853"/></linearGradient>
  </defs>
  <g stroke="url(#bs-g1)" stroke-width="2" stroke-linecap="round" opacity="0.55">
    <line x1="60" y1="60" x2="140" y2="100"/><line x1="140" y1="100" x2="220" y2="50"/>
    <line x1="140" y1="100" x2="210" y2="160"/><line x1="140" y1="100" x2="70" y2="155"/>
    <line x1="60" y1="60" x2="70" y2="155"/><line x1="220" y1="50" x2="210" y2="160"/>
  </g>
  <rect x="96" y="132" width="88" height="44" rx="8" fill="#4285F4" opacity="0.08"/>
  <g>
    <circle class="bs-float" cx="140" cy="100" r="18" fill="#4285F4"/>
    <circle class="bs-float d1" cx="60" cy="60" r="11" fill="#34A853"/>
    <circle class="bs-float d2" cx="220" cy="50" r="13" fill="#FBBC05"/>
    <circle class="bs-float d3" cx="210" cy="160" r="10" fill="#EA4335"/>
    <circle class="bs-float d1" cx="70" cy="155" r="8" fill="#00BCD4"/>
  </g>
  <circle cx="140" cy="100" r="30" fill="none" stroke="#4285F4" stroke-width="1.5" opacity="0.25"/>
</svg>
"""


def chips(items: Iterable[tuple[str, str] | tuple[str, str, str]]) -> str:
    """HTML de chips ``(icono, texto[, tono])``; tonos: blue, green, yellow, red."""
    parts = []
    for item in items:
        name, text, *tone = item
        tone_attr = f' data-tone="{escape(tone[0])}"' if tone else ""
        parts.append(f'<span class="bs-chip"{tone_attr}>{icon(name, 14)}{escape(text)}</span>')
    return f'<div class="bs-chips">{"".join(parts)}</div>'


def page_header(
    title: str,
    subtitle: str,
    *,
    eyebrow: str = "BankShield Analytics",
    highlight: str | None = None,
    badges: Iterable[tuple[str, str] | tuple[str, str, str]] = (),
    visual: bool = True,
) -> None:
    """Cabecera hero: texto a la izquierda y visual abstracto a la derecha.

    ``highlight`` es una parte de ``title`` que se pinta con el degradado de marca.
    """
    safe_title = escape(title)
    if highlight and highlight in title:
        safe_title = safe_title.replace(
            escape(highlight), f'<span class="bs-gradient-text">{escape(highlight)}</span>', 1
        )
    badge_html = chips(badges) if badges else ""
    visual_html = f'<div class="bs-hero-visual">{_hero_visual()}</div>' if visual else ""
    st.markdown(
        f'<section class="bs-hero">'
        f'<div><span class="bs-hero-eyebrow">{icon("sparkles", 14)}{escape(eyebrow)}</span>'
        f'<h1 class="bs-hero-title">{safe_title}</h1>'
        f'<p class="bs-hero-sub">{escape(subtitle)}</p>{badge_html}</div>'
        f"{visual_html}</section>",
        unsafe_allow_html=True,
    )


def module_cards(modules: Iterable[dict]) -> None:
    """Cuadrícula de tarjetas: ``icon``, ``title``, ``text`` y ``tone`` opcional."""
    cards = []
    for module in modules:
        tone = escape(module.get("tone", "blue"))
        cards.append(
            f'<article class="bs-card bs-module" data-tone="{tone}">'
            f'<div class="bs-module-icon">{icon(module["icon"], 22)}</div>'
            f'<div><h4>{escape(module["title"])}</h4><p>{escape(module["text"])}</p></div>'
            "</article>"
        )
    st.markdown(f'<div class="bs-module-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def ai_loading(label: str = "Procesando…") -> None:
    """Indicador de carga con la barra degradada del design system."""
    st.markdown(
        f'<div role="status" aria-live="polite"><div class="ai-loading-animation"></div>'
        f'<small style="color: var(--muted)">{escape(label)}</small></div>',
        unsafe_allow_html=True,
    )


def status_notice(state: str, title: str, detail: str) -> None:
    """Estado identificado por icono, texto y color; legible en ambos temas."""
    symbol = icon(NOTICE_ICONS[state], 18)
    st.markdown(
        f'<div class="bs-notice" data-state="{state}" role="status">'
        f'<div class="bs-notice-title">{symbol}{escape(title)}</div>'
        f'<div class="bs-notice-detail">{escape(detail)}</div></div>',
        unsafe_allow_html=True,
    )
