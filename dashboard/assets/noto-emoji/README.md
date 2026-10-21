# Google Noto Emoji — iconos de la demo

Fuente oficial: [Noto Emoji en Google Fonts](https://github.com/google/fonts/tree/main/ofl/notoemoji). Licencia incluida en [OFL.txt](OFL.txt).

`NotoEmoji-Demo.ttf` contiene un subconjunto de los símbolos usados en las pantallas, instanciado a peso 400 desde la fuente variable monocromática `NotoEmoji[wght].ttf`. Los PNG de las pestañas se renderizan a partir del mismo subconjunto en gris, sobre fondo transparente.

`bankshield.ui.configure_page` incluye la fuente local mediante CSS y utiliza esos PNG como favicons. Los textos normales conservan su tipografía; los emojis usan los contornos monocromáticos de Google y heredan el color del texto. No se requiere consultar Google Fonts durante la demo.

`bankshield.ico` reutiliza el PNG de escudo en tamaños 16–64 px para los accesos de abrir/cerrar el sistema en Windows.
