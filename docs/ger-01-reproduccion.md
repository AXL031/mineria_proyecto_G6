# GER-01 — preparación verificable y entorno fijado

Estado al 2 de noviembre de 2026: implementación y validación local del alcance
`current` completadas, con evidencias bajo `artifacts/reports/ger-01/`. Las entregas CUE-01,
SEV-01 y RHA-01 todavía no están disponibles en esta rama. GER-01 no acredita
su preparación ni aceptación humana, CI remoto o ejecución en otra PC.

## Preparador

```powershell
.venv-pruebas/Scripts/python.exe scripts/prepare_demo.py --plan
.venv-pruebas/Scripts/python.exe scripts/prepare_demo.py
.venv-pruebas/Scripts/python.exe scripts/prepare_demo.py --stage analytics-d1
.venv-pruebas/Scripts/python.exe scripts/prepare_demo.py --stage fraud-training --force
.venv-pruebas/Scripts/python.exe scripts/prepare_demo.py --scope full
```

El alcance predeterminado `current` prepara los seis módulos existentes y D1.
Registra las ampliaciones ausentes como `skipped_optional` **solo respecto de
ese alcance**. Siguen siendo requisitos del cierre ampliado. `full` exige las
tres entregas: si falta un CLI/configuración/contrato, falla antes de entrenar
y publica el motivo. Seleccionar explícitamente una de esas ampliaciones con
`--stage` también exige su entrega. GER-02 permanece P2 y su historial inmutable
se ejecutará mediante su CLI propia cuando exista; el DAG registra su dependencia
de las predicciones de regresión, sin anunciarlo como implementado.

Dependencias principales:

- Bronze transaccional → Silver → D1 → asociaciones y regresión.
- Silver → Gold temporal y monitoreo histórico; Silver → mart → segmentos.
- Bronze crediticio → Silver crédito → modelo y métricas.
- Bronze reclamos → Silver reclamos → clasificador → ejemplos.
- Bronze PaySim → perfil completo; Silver + perfil → fraude → patrones manuales.
- Bronze de redes → comparación con `limit=10000`.
- Predicciones de regresión → historial recomendado GER-02, pendiente de entrega.

`--stage` incluye las dependencias. `--force` reconstruye toda esa selección,
**incluido fraude**, a diferencia del preparador anterior. Sin `--force`, una
etapa solo se reutiliza si coincide su recibo local de versión 1:

- SHA-256 de cada entrada, configuración canónica y fuentes de código declaradas.
- Versiones del entorno e identidad de la receta (comando, contratos, dependencias).
- SHA-256 y tamaño de todas las salidas; versión JSON, controles de calidad y
  vínculos de fuente/modelo cuando el productor los publica; Parquet legible.

Los artefactos históricos sin recibo **se reconstruyen una vez**. En particular,
Gold temporal, monitoreo y segmentos antiguos no conservan toda la identidad de
configuración/entrada que exige el nuevo recibo. No se adopta compatibilidad por
nombre de archivo ni se atribuyen metadatos nuevos a una ejecución histórica.
Una salida borrada/modificada, metadatos incompatibles o una receta distinta
invalidan el reuso. Si un comando termina en cero pero no publica todas sus
salidas, falla; sus dependientes no se ejecutan. También se rechazan cambios de
entrada/configuración durante una ejecución.

Los scripts corren offline con argumentos estructurados y `cwd` del proyecto.
Los GET de la aplicación siguen leyendo artefactos. Los reportes Markdown de la
preparación se redirigen a `artifacts/reports/demo/`. Los CLI futuros deben
aceptar el desvío de Markdown antes de habilitar su preparación; no se modifica
su implementación en nombre de otro integrante.

## Manifiesto y recursos

`artifacts/reports/demo/preparation-manifest.json` se publica atómicamente y
también al fallar. Contiene el alcance, selección/orden, entorno, estados
`built`, `reused`, `failed`, `skipped_optional`, huellas, motivo de reuso o
reconstrucción, comienzo/fin UTC, duración, código de salida, logs y error.
Los recibos están en `artifacts/reports/demo/receipts/`.
Cada corrida conserva sus propios logs en
`artifacts/reports/demo/runs/<run_id>/`; una reutilización posterior no los sobrescribe.

Se registra espacio libre inicial/final, bytes de salidas declaradas y RSS
aproximado de proceso e hijos, muestreado cada 0.2 segundos cuando está
disponible `psutil`. La suma RSS puede contar memoria compartida más de una vez
y omitir picos entre muestras; no representa RAM mínima garantizada. Si no se
mide, `peak_rss_bytes` es `null`. Una etapa reutilizada no ejecuta el productor
ni tiene una nueva medición de su memoria.

## Lock de Python 3.12 / Windows

`requirements/lock-py312-windows.txt` fija 83 paquetes, incluidos pip,
setuptools y wheel. Procede de un entorno nuevo instalado con versiones exactas;
se excluye el proyecto editable del archivo. No contiene rutas personales,
URLs de instalación ni credenciales. Los rangos de desarrollo se conservan.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1 -UseLock
# Entorno alternativo dentro del proyecto, sin sustituir el existente:
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1 -UseLock -EnvironmentDirectory artifacts/reports/ger-01/lock-env
```

Con `-UseLock`, el instalador exige Python 3.12, instala los pines y después
el proyecto local con `--no-deps --no-build-isolation`; ejecuta `pip check` y
la suite completa. No actualiza pip a una versión ajena al lock. Sin ese flag
conserva la instalación por rangos. `-SkipTests` permite instalación explícita
sin suite, pero no permite declarar el entorno validado. `-PythonExecutable`
admite un intérprete instalado si no existe `py -3.12`.

CI tiene un trabajo Windows/Python 3.12 con lock y otro con rangos. Ambos usan
fixtures; no descargan LFS ni entrenan los originales. La ejecución remota
seguirá pendiente hasta publicar y consultar un resultado real.

## Verificación y cierre

La suite completa del entorno nuevo pasó 285 pruebas; la instalación explícita
`-UseLock` y `pip check` también pasaron. Logs: `setup-lock-validation.log`,
`lock-install.log` y `project-install.log`, bajo el directorio de evidencia local.
El entorno habitual `.venv-pruebas` también se alineó con el lock. La suite final,
incluida la regresión que impide sobrescribir logs anteriores, pasó **286 pruebas**
en 67.038 s (`final-suite.log`).

Preparación principal y segunda pasada verificadas:

| Evidencia | Resultado observado |
| --- | --- |
| `preparation-real.json` | 14 etapas construidas, 4 ampliaciones omitidas explícitamente en `current`; 772.388 s. |
| `preparation-reuse.json` | Las mismas 14 etapas reutilizadas por recibos/contratos; 6.270 s. |
| Salidas declaradas | 805,482,895 bytes (0.750 GiB); excluye entornos, cachés y copias Bronze. |
| Mayor RSS observado por etapa | 1.991 GiB, en segmentos; medición aproximada según el alcance descrito arriba. |
| `delivery-check.json` | 48 comprobaciones HTTP/páginas de los seis módulos, mediante el verificador de Angel. |
| `forecast-after-preparation.json` | 71 comprobaciones temporales aprobadas tras regenerar Gold y monitoreo; comparación histórica compatible. |
| D1 completo | 6,362,620 filas, nueve controles y las tres huellas iguales a la entrega documentada por Taco. |
| `full-preflight.json` | Fallo esperado antes de entrenar por entregas CUE-01/SEV-01/RHA-01 pendientes; no declara `full` disponible. |

El inventario de versiones, tiempos por etapa y memoria está en `resources.json`.
No se midió el espacio del entorno instalado; no se inventa una cifra para él.
Estas duraciones describen esta ejecución y no son garantías para otra PC.
La demo principal se verificó en API `http://127.0.0.1:8010` y panel
`http://127.0.0.1:8501`: el puerto 8000 pertenecía a otros procesos y se conservó.
Para verificar esa instancia, usar `scripts/verify_demo.py --api-url http://127.0.0.1:8010`.

Las 16 pruebas de `test_preparation.py` usan scripts mínimos y directorios
temporales, sin entrenamiento pesado. Cubren orden, reuso, fuerza, cambios de
entrada, configuración, código y entorno, salida incompleta/alterada,
identidades incompatibles, fallo del productor, dependientes detenidos, ciclos,
entregas opcionales/obligatorias y protección de rutas Bronze/documentación.

## Reproducción aislada local comprobada

Se creó un clon independiente de la rama local `gerardo` con `--no-hardlinks`,
sin copiar Silver, Gold, modelos ni entornos. Los tres originales llegaron
mediante `git lfs pull` desde GitHub y se creó otra `.venv-pruebas` con `-UseLock`.
Su instalación pasó `pip check` y 285 pruebas, antes de añadir la última prueba
de conservación de logs. El código versionado del clon permaneció limpio.

| Evidencia | Resultado |
| --- | --- |
| Código de modelos reproducido | Commit `6c1202e`; las mejoras finales de conservación de logs no cambian los productores/modelos. |
| `clean-preparation.json` | 14 etapas reconstruidas desde cero; 678.967 s; cuatro ampliaciones explícitamente pendientes. |
| `reproduction-comparison.json` | 28 comprobaciones aprobadas: mismos originales, Silver, D1, bins, entorno, configuración, particiones y métricas de validation/test de fraude, crédito y reclamos. |
| Tolerancia de comparación numérica | `rtol=1e-9`, `atol=1e-9`; no se exige igualdad binaria de modelos con metadatos de procedencia distintos. |
| `clean-delivery-check.json` | 48 comprobaciones de API y páginas en `8011`/`8502`; los servidores del clon se detuvieron al terminar. |
| Archivo de evidencia | Logs de cada etapa en `clean-stage-logs/`, métricas completas en `clean-model-metrics/`, metadatos de D1 y Silver en `clean-analytics-*.json` y `clean-silver-quality.json`. |

Esto acredita una **reproducción aislada local en esta misma PC**. No acredita
una segunda persona, otra PC, aceptación de Sevan/Taco o CI remoto.
Las carpetas de entorno/clon utilizadas solo para esta prueba son temporales;
se conserva la evidencia fuera de ellas y el entorno habitual queda instalado
con el lock. Los datos y modelos principales de la demo permanecen disponibles.

Para repetir una reproducción aislada, partir de una copia versionada que
contenga GER-01, instalar LFS y usar un directorio nuevo:

```powershell
$source = (Get-Location).Path
$clone = Join-Path $source 'artifacts/reports/ger-01/clean-clone'
$env:GIT_LFS_SKIP_SMUDGE = '1'
git clone --no-hardlinks --branch gerardo "$source" "$clone"
Remove-Item Env:GIT_LFS_SKIP_SMUDGE
git -C "$clone" remote set-url origin https://github.com/AXL031/mineria_proyecto_G6.git
git -C "$clone" lfs pull
powershell -ExecutionPolicy Bypass -File "$clone/scripts/setup_env.ps1" -UseLock -PythonExecutable "$source/.venv-pruebas/Scripts/python.exe"
& "$clone/.venv-pruebas/Scripts/python.exe" "$clone/scripts/prepare_demo.py" --scope current
powershell -ExecutionPolicy Bypass -File "$clone/scripts/start_demo.ps1" -ApiPort 8011 -DashboardPort 8502
& "$clone/.venv-pruebas/Scripts/python.exe" "$clone/scripts/verify_demo.py" --api-url http://127.0.0.1:8011
powershell -ExecutionPolicy Bypass -File "$clone/scripts/stop_demo.ps1"
```

Para cerrar GER-01 con el equipo:

1. Taco revisa el flujo; Sevan revisa versiones/modelos; una segunda persona
   confirma la reproducción. No marcar esas revisiones por una corrida automática.
2. Cuando lleguen las tres ampliaciones, integrar sus CLI/metadatos acordados,
   repetir `--scope full` y ejecutar la verificación central ampliada de Angel.
3. Comprobar CI remoto después de publicar los commits y registrar sus resultados.

Docker/Compose permanece P2 opcional y no se añade como requisito de cierre.
