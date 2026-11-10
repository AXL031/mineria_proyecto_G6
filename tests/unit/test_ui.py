"""Pruebas del design system compartido (bankshield.ui)."""

import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from bankshield import ui

EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿]")


class DesignSystemTests(unittest.TestCase):
    def test_css_declares_design_system_variables(self):
        css = ui.design_css()
        for token in ("--brand-blue: #4285F4", "--brand-red: #EA4335", "--brand-yellow: #FBBC05",
                      "--brand-green: #34A853", "--white: #FFFFFF", "--light-grey: #F8F9FA",
                      "--font-sans: Roboto, Arial, sans-serif",
                      "--shadow-material: 0 2px 4px rgba(0,0,0,0.1)"):
            self.assertIn(token, css)
        for selector in (".ai-loading-animation", ".material-ripple-effect", ".bs-hero"):
            self.assertIn(selector, css)
        self.assertEqual(css.count("{"), css.count("}"))

    def test_dark_theme_changes_surfaces_only(self):
        light, dark = ui.design_css(False), ui.design_css(True)
        self.assertIn("--surface: #FFFFFF", light)
        self.assertIn("--surface: #1F2023", dark)
        self.assertIn("--brand-blue: #4285F4", dark)

    def test_css_respects_reduced_motion(self):
        self.assertIn("prefers-reduced-motion", ui.design_css())

    def test_page_icons_are_material_icons(self):
        for value in ui.PAGE_ICONS.values():
            self.assertRegex(value, r"^:material/[a-z_]+:$")

    def test_icons_are_inline_svg_and_decorative_by_default(self):
        svg = ui.icon("shield")
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn('aria-hidden="true"', svg)
        self.assertIn('aria-label="Escudo"', ui.icon("shield", label="Escudo"))
        with self.assertRaises(KeyError):
            ui.icon("no-existe")

    def test_chips_escape_text_and_accept_tone(self):
        html = ui.chips([("info", "<b>x</b>"), ("alert", "Aviso", "yellow")])
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", html)
        self.assertIn('data-tone="yellow"', html)
        self.assertIsNone(EMOJI.search(html))

    def test_page_header_highlights_and_escapes(self):
        with patch.object(ui.st, "markdown") as markdown:
            ui.page_header("Redes <script>", "Sub & más", highlight="Redes")
        html = markdown.call_args.args[0]
        self.assertIn('<span class="bs-gradient-text">Redes</span>', html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("Sub &amp; más", html)
        self.assertIn("bs-hero-visual", html)

    def test_status_notice_uses_svg_icon_and_keeps_text(self):
        with patch.object(ui.st, "markdown") as markdown:
            ui.status_notice("warning", "Título", "Detalle <i>")
        html = markdown.call_args.args[0]
        self.assertIn('data-state="warning"', html)
        self.assertIn("<svg", html)
        self.assertIn("Título", html)
        self.assertIn("Detalle &lt;i&gt;", html)
        self.assertIsNone(EMOJI.search(html))

    def test_portal_and_graph_page_have_no_emoji_text(self):
        for path in ("dashboard/app.py", "dashboard/inicio.py", "dashboard/pages/03_redes.py"):
            text = (ROOT / path).read_text(encoding="utf-8")
            text = re.sub(r'page_icon="[^"]*"', "", text)
            self.assertIsNone(EMOJI.search(text), path)

    def test_streamlit_theme_uses_brand_palette(self):
        config = (ROOT / ".streamlit/config.toml").read_text(encoding="utf-8")
        self.assertIn('primaryColor = "#4285F4"', config)
        self.assertIn('textColor = "#3C4043"', config)
        self.assertIn("[theme.dark]", config)

    def test_navigation_lists_every_page_with_title_icon_and_route(self):
        router = (ROOT / "dashboard/app.py").read_text(encoding="utf-8")
        pages = re.findall(r'st\.Page\("([^"]+)", title="([^"]+)", icon=":material/[a-z_]+:"', router)
        paths = {path for path, _ in pages}
        expected = {"inicio.py"} | {f"pages/{p.name}" for p in (ROOT / "dashboard/pages").glob("*.py")}
        self.assertEqual(paths, expected)
        for path in paths:
            self.assertTrue((ROOT / "dashboard" / path).is_file(), path)
        for route in ("fraude", "credito", "redes", "pronosticos", "reclamos", "segmentos", "regresion"):
            self.assertIn(f'url_path="{route}"', router)
        self.assertTrue((ROOT / "dashboard/assets/bankshield-logo.svg").is_file())

    def test_streamlit_toolbar_hides_deploy(self):
        config = (ROOT / ".streamlit/config.toml").read_text(encoding="utf-8")
        self.assertIn('toolbarMode = "minimal"', config)


if __name__ == "__main__":
    unittest.main()
