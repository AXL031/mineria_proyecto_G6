# Design system del panel: «Estilo Material AI»

Guía visual del panel de Streamlit de BankShield. Se adaptó un design system pensado para landing pages a un panel analítico: se conservan las páginas, su contenido en español y sus contratos HTTP; cambia solo la capa visual.

## Dónde vive

| Pieza | Archivo | Qué hace |
| --- | --- | --- |
| Tema de Streamlit | `.streamlit/config.toml` | Paleta, tipografía, radio y colores de gráficos, en claro y oscuro. Se lee al iniciar Streamlit desde la raíz. |
| Capa compartida | `src/bankshield/ui.py` | Variables CSS y estilos de componentes que inyecta `configure_page`, más los componentes reutilizables. |
| Pruebas | `tests/unit/test_ui.py` | Variables, componentes, escape de HTML y ausencia de emojis. |

Toda página que llama a `configure_page` recibe el diseño sin cambiar su lógica.

## Navegación y barra superior

- `dashboard/app.py` define el menú con `st.navigation`: Inicio y las secciones Riesgo y fraude, Transacciones y Texto. Cada página tiene título legible e icono Material, y conserva su ruta (`/fraude`, `/credito`, `/redes`…). La portada vive en `dashboard/inicio.py` y el logo en `dashboard/assets/bankshield-logo.svg`.
- Para agregar una página: crear el script en `dashboard/pages/` y registrarlo en `PAGES` de `dashboard/app.py`. La prueba `tests/unit/test_ui.py` falla si una página queda fuera del menú.
- `toolbarMode = "minimal"` oculta «Deploy» y las opciones de desarrollador. El indicador de ejecución se muestra como la barra degradada de carga.

## Variables

```css
--brand-blue: #4285F4;   --brand-red: #EA4335;   --brand-yellow: #FBBC05;
--brand-green: #34A853;  --white: #FFFFFF;       --light-grey: #F8F9FA;
--font-sans: Roboto, Arial, sans-serif;
--shadow-material: 0 2px 4px rgba(0,0,0,0.1);
```

Además: `--dark-grey: #3C4043` (texto), `--brand-cyan: #00BCD4` (uso decorativo), `--gradient-brand` (azul → verde) y radios de 8, 16 y 24 px.

## Uso semántico del color

- **Azul:** acción principal, enlaces, foco y pestaña activa.
- **Rojo:** errores y fraude etiquetado.
- **Amarillo:** advertencias y selección en el subgrafo.
- **Verde:** éxito y acentos secundarios.

## Componentes

- `page_header(title, subtitle, eyebrow=..., highlight=..., badges=...)`: cabecera hero con texto a la izquierda e ilustración abstracta de datos con nodos flotantes a la derecha.
- `chips([(icono, texto, tono?)])`: etiquetas como «Datos simulados».
- `module_cards([...])`: tarjetas con icono de color (portada).
- `status_notice(estado, título, detalle)`: avisos con icono SVG.
- `ai_loading(texto)` y la clase `.ai-loading-animation`: barra degradada de carga. Reemplaza el spinner circular de `st.spinner`.
- `.material-ripple-effect`: efecto ripple, aplicado también a los botones de Streamlit.
- `icon(nombre)`: SVG en línea estilo Lucide.

Los elementos nativos de Streamlit también se estilizan:

- **Métricas:** como tarjetas, con acento de color por columna.
- **Pestañas, botones y campos:** pestañas, botones con elevación al pasar el cursor y campos con anillo de foco de 2 px.
- **Contenedores:** tablas, expanders, formularios, avisos `st.info`/`st.warning`/`st.error` y el menú lateral.

## Reglas

- **Sin emojis en la interfaz:** usar `:material/nombre:` en etiquetas de Streamlit o `icon()` en HTML.
- **Sin recursos externos:** no se descargan fuentes ni bibliotecas durante la demo. Si Roboto no está instalada, se usa Arial.
- **Animaciones:** de 200 a 420 ms, solo sobre `transform`, `opacity`, sombras y colores. Se desactivan con `prefers-reduced-motion`.
- **Diseño adaptable:** por debajo de 768 px la cabecera y las tarjetas pasan a una columna.

## Estado por página

| Página | Estado |
| --- | --- |
| Portada (`dashboard/inicio.py`) | Rediseñada con cabecera hero, aviso y tarjetas de módulo. |
| 03 Redes | Rediseñada: cabecera hero, iconos Material y paleta de marca en el subgrafo. |
| 01, 02, 04, 05, 06, 07 | Reciben el diseño desde la capa compartida (títulos, métricas, avisos, tablas, botones). Sus responsables pueden adoptar `page_header` y los iconos Material cuando lo decidan. |
