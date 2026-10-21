# Demo local de BankShield — 13 de octubre de 2026

> Esta guía describe la demo existente de seis módulos. Las ampliaciones de regresión, asociaciones descubiertas y comparación de grafos están pendientes según [el backlog del 20 de octubre](pendientes-cierre-2026-10-20.md). Angel actualizará el guion y Gerardo la preparación cuando se implementen; los comandos de esas capacidades nuevas no se consideran disponibles por estar especificados.

## Abrir y arrancar

En esta carpeta del proyecto hay dos accesos: **Abrir BankShield** y **Cerrar BankShield**. Abrir inicia API/panel en segundo plano y muestra el navegador; si ya está iniciado, reutiliza la instancia. Cerrar detiene ambos procesos y sus hijos, y confirma el cierre. No se borran datos ni modelos. En el Explorador de Windows, se activan como cualquier acceso directo, normalmente con doble clic.

Para recrearlos si cambia la ubicación de la carpeta:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/create_demo_shortcuts.ps1
```

Panel: **http://127.0.0.1:8501**. API interactiva: **http://127.0.0.1:8000/docs**.

La preparación de esta PC usa los CSV completos, Silver transaccional existente y artefactos reconstruidos de crédito, temporal, segmentos y reclamos. Los seis módulos tienen página y endpoints. El entrenamiento y las transformaciones se hacen antes de presentar.

Desde PowerShell en la raíz del proyecto:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_demo.ps1
```

El arranque comprueba los archivos requeridos, configura el modelo de fraude-Silver, usa redes de 10,000 transacciones como muestra inicial y levanta API/panel en localhost sin ventanas adicionales. Se detiene si los puertos están ocupados; no termina servicios ajenos. Guarda los identificadores y fecha de inicio de sus procesos para poder detenerlos con seguridad.

Para detener:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop_demo.ps1
```

Para ensayar los seis recorridos con los modelos reales y las páginas:

```powershell
.venv-pruebas/Scripts/python.exe scripts/verify_demo.py
```

La API debe estar iniciada. Evidencia local: `artifacts/reports/demo/delivery-check.json` y `verification.log`. El ensayo comprueba respuestas HTTP, identidad del modelo, ejemplos válidos e inválidos y controles de las seis páginas mediante AppTest contra HTTP real.

## Guion de 12–15 minutos

| Orden | Pantalla y acción | Qué explicar |
| --- | --- | --- |
| 1 | Portada: presentar los seis módulos y las tres fuentes | Plataforma analítica académica; fuentes separadas, sin llave común de clientes. |
| 2 | Fraude: evaluar las dos operaciones siguientes y consultar métricas/patrones | Variables disponibles antes de la operación, score, umbral fijado en validación y errores. |
| 3 | Redes: mantener muestra de 10,000 y consultar `C985934102` | Conexiones, flujos, subgrafo y alertas exploratorias de cuentas simuladas. |
| 4 | Segmentos: comparar ambos grupos y explorar sus cuentas | Cuantiles como referencia; KMeans sin etiqueta de fraude; perfiles y estabilidad. |
| 5 | Pronósticos: generar 24 steps de cantidad y después monto; consultar monitoreo | Naive se seleccionó al superar por MAE a Holt-Winters; cambio histórico del tramo final. |
| 6 | Crédito: evaluar el perfil predeterminado y consultar métricas | Probabilidad calibrada y factores descriptivos; no determina un monto de crédito. |
| 7 | Reclamos: clasificar la narrativa predeterminada y consultar tendencias, evaluación y ejemplos | Producto sugerido por texto en inglés, cobertura de narrativas y errores reales. |

### Fraude: ejemplos comprobados

| Tipo | Monto | Saldo anterior del origen | Resultado esperado con el modelo preparado |
| --- | ---: | ---: | --- |
| TRANSFER | 1000.00 | 500.00 | Sin alerta |
| TRANSFER | 36942.13 | 36942.13 | Alerta |

Las alertas dependen del modelo cargado. El arranque configura `artifacts/models/fraud-silver/model.joblib`, con su reporte compatible de patrones. Consultar las métricas de ese mismo artefacto.

### Crédito: perfil comprobado

Edad 30; ingreso anual 55,000; vivienda RENT; antigüedad laboral 4 años; historial 5 años; finalidad PERSONAL; monto 10,000; impago previo N. Resultado reconstruido: probabilidad 6.09%, umbral 15.53%, riesgo bajo. Los factores por oclusión explican el comportamiento del modelo, sin interpretación causal.

### Segmentos y pronósticos

Segmentos: 146,629 cuentas con diez o más operaciones recibidas, k=2, silueta 0.2305 y ARI medio 0.7280. Ejemplo comprobado: segmento 0, cuenta `C1286084959`. La variable de fraude solo describe los grupos tras formarlos; no participa del agrupamiento.

Monitoreo: seis indicadores detectan cambios al comparar steps 694–718 con 719–743. Son horas simuladas; el cierre contiene solo fraude y no representa un monitor de producción. La proyección expuesta continúa desde la última observación disponible; no debe confundirse con el backtesting de la ventana operativa ni presentarse como liquidez bancaria.

### Reclamos: ejemplo comprobado

Usar la narrativa precargada:

> My credit report contains an account that does not belong to me. I disputed the incorrect information with the credit bureau but it has not been removed.

Producto sugerido: **Credit reporting**. La puntuación es una salida no calibrada del clasificador; no representa una certeza de resolución. El modelo se entrenó con narrativas en inglés. No promete rendimiento en español.

Consultar tendencias: 555,957 reclamos, 66,806 con narrativa (12.02%), periodo 2011-12-01 a 2016-04-25. La evaluación reconstruida da macro-F1 0.7278, frente a 0.6677 de Naive Bayes y 0.0369 de la referencia trivial. Los ejemplos muestran aciertos y errores de la prueba; su revisión humana cruzada sigue pendiente.

## Recuperar artefactos en otra copia

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1
.venv-pruebas/Scripts/python.exe scripts/prepare_demo.py
```

Requiere Bronze completo mediante Git LFS. La preparación reutiliza los artefactos existentes; `--force` reconstruye las etapas y puede tardar y consumir memoria. Las ejecuciones guardan sus logs y Markdown en `artifacts/reports/demo/`, evitando sustituir reportes versionados. Tras preparar, ejecutar arranque y verificación. No copiar un entorno virtual entre PCs.

## Alcance de la evidencia

Se reconstruyeron crédito, Gold temporal/monitoreo, mart/segmentos y Silver/modelo/ejemplos de reclamos. Se reutilizaron Silver transaccional y fraude-Silver previamente verificados. El ensayo local pasó 48 comprobaciones; el log y JSON quedan excluidos de Git. No equivale a un clon limpio en una segunda PC, a Docker validado ni a aceptación humana del equipo.

La API y el panel quedan en localhost. Para una presentación local, basta abrir el panel y recorrer el guion. Mantener visibles las limitaciones de fuente, simulación y modelos, y explicar los tres dominios como fuentes independientes.
