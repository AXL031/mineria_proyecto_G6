# Encargo de Angel — integración, aceptación NLP y evidencia final

Estado inicial: pendiente. Leer [contratos y prioridades](../pendientes-cierre-2026-10-20.md). Reclamos ya tiene servicio/API/página y artefactos locales: preservar esa implementación. Cada dueño entrega su capacidad y sus pruebas; Angel integra navegación, contratos centrales y demostración.

## ANG-01 — integración central y verificación (P1)

### Archivos y límites

Responsable de `api/main.py`, `dashboard/app.py`, `scripts/verify_demo.py`, `api/README.md`, `dashboard/README.md` y `docs/demo-local.md`. Coordinar con Gerardo variables y scripts de arranque/parada. No editar al mismo tiempo páginas de Cueva, Rhamses, Gerardo o Sevan; enviarles cambios concretos de contrato/etiquetas si hacen falta. Gerardo mantiene el preparador y entorno.

### Integración paso a paso

1. Revisar con los responsables los archivos locales sin commit, especialmente reclamos y scripts de demo, para que formen parte de la entrega compartida. No hacer commit indiscriminado de output, tmp, datasets, logs o cambios ajenos. Preparar cambios revisables; publicar según autorización vigente del equipo, sin presumir una autorización nueva de push/merge a partir de este documento.
2. Registrar `regression_router` de Sevan con prefijo `/api` en `api/main.py`. Asociaciones vive dentro del router de fraude; comparación dentro del de grafos. Si GER-02 se entrega, registrar su router de monitoring; si está pendiente, no importar un módulo inexistente.
3. Actualizar raíz `/`: conservar los seis módulos históricos y agregar `regression` una vez implementado. Añadir una lista `capabilities` para distinguir `association_mining`, `graph_comparison` y, solo cuando exista, `model_performance_monitoring`. Una capacidad registrada no garantiza artefacto listo: mantener enlaces a endpoints de estado/evaluación.
4. Actualizar portada/navegación: conservar seis páginas y enlazar `07_regresion.py`; reglas descubiertas dentro de Fraude; evaluación en Redes; historial P2 dentro de Pronósticos. No crear páginas vacías ni anunciar capacidades futuras como terminadas. Mantener componentes de `bankshield.ui` actuales.
5. Asegurar por revisión de código y pruebas que formularios/consultas usan HTTP, con timeout y mensajes específicos ante 422/404/503. Una capacidad sin modelo debe mostrar aviso y permitir navegar a las demás; no exigir todos los modelos al importar la API.
6. Preservar resultados de formularios en session_state cuando se consultan métricas. Cuando cambie model_id/analysis_id o filtro/periodo, señalar que un resultado anterior corresponde a otra consulta; no mezclar evaluaciones de artefactos distintos.
7. Ajustar `scripts/verify_demo.py`: su comprobación actual exige exactamente seis módulos y usa índices de botones. Pasar a comprobar módulos/capacidades esperadas por perfil y seleccionar widgets por etiquetas o keys estables, coordinadas con cada dueño. No debilitar la verificación para que un endpoint faltante pase.
8. Perfil de verificación por defecto: seis capacidades base + regresión + asociaciones + comparación de grafos. Agregar `--include-model-monitoring` para exigir el P2 cuando se haya implementado/preparado; si no se pide, registrar `skipped_optional` explícito en el reporte. No omitir silenciosamente pruebas de P0/P1.
9. Escribir resultado aunque falle: revisión/estado del árbol, UTC, API URL, IDs de modelos/análisis, perfil, checks, casos, error y capacidades opcionales omitidas. No usar cifras históricas como nuevos resultados.

### Casos reales que debe verificar

| Capacidad | Recorrido mínimo |
| --- | --- |
| Seis módulos existentes | Conservar checks actuales de predicción, consultas, segmentos, proyección, monitoreo histórico, NLP e interacciones de página. |
| Regresión | GET model; POST type/saldo; prediction finita no negativa; mismo model_id; GET examples paginado; rechazar amount extra y saldo negativo con 422. |
| Asociaciones | GET de test y otra partición; analysis_id coherente; paginación; lista vacía válida; rechazo de partición inválida. Verificar selección documentada en validation, no asumir que test tenga reglas exitosas. |
| Grafos | GET evaluation con limit=10000; mismo universo y k para red/referencia; límite de muestra incompatible produce 503; las otras consultas siguen funcionando. |
| P2 desempeño | Si se solicita: historial real, detalle, identidad del modelo y al menos ejecución evaluada; lista vacía no acredita demostración completa de P2. |
| Páginas | Inicialización e interacciones reales de las siete páginas; probar las secciones nuevas además de cargar la portada. |

Los errores por ausencia de artefacto deben probarse con dependencias/rutas temporales en tests o proceso aislado; no renombrar/borrar modelos del usuario para provocar errores de la demo.

### Pruebas y cierre

- Crear `tests/unit/test_delivery_contracts.py` con TestClient, dependencias controladas y fixtures: routers registrados, raíz coherente, contratos y ausencia de una capacidad sin romper otras.
- Ampliar AppTest de portada/navegación y verificar selección por labels/keys; cada dueño mantiene pruebas de su propia página.
- Coordinar suite completa y demo real con Gerardo; guardar logs y JSON sin publicar datos sensibles o textos de entrada innecesarios.
- Ejecutar recorrido visual en navegador y documentar errores/estados observados; AppTest por sí solo no se declara revisión visual humana.
- Rhamses revisa navegación/HTTP; Gerardo revisa integración y reproducción. Evidencia final debe corresponder a la revisión final del código.

## ANG-02 — cierre de reclamos y aceptación humana (P1)

- [ ] Revisar humanamente ejemplos ya extraídos en `docs/reclamos/revision-ejemplos.md`: aciertos, confusiones frecuentes, errores de alta confianza y casi duplicados. Registrar quién revisa, fecha, caso, conclusión y límites. El agente prepara la tabla y observaciones, pero no firma como una persona.
- [ ] Confirmar fuente/versión y condiciones de uso de la copia CFPB; registrar respaldo en `docs/datasets.md`. No inferir fecha exacta de descarga a partir de fechas del contenido.
- [ ] Revisar servicio/API/página existentes con Rhamses, incluyendo modelo ausente, narrativa corta/no reconocida, tendencias y ejemplos.
- [ ] Preservar anonimización, marcadores y límites: idioma inglés, scores no calibrados, cobertura parcial de narrativas y diferencias entre producto sugerido y resolución del reclamo.
- [ ] Precisar en el informe la separación por primera aparición de textos idénticos: no llamarla corte cronológico estricto de todas las filas, porque las fechas pueden solaparse entre particiones.
- [ ] Reproducir etapa NLP en el segundo entorno y registrar aceptación real; no volver a asignar la creación de la página como pendiente.

## ANG-03 — matriz de requisitos y material de entrega (P1)

Crear `docs/matriz-entregables.md` con columnas: semana/requisito del PDF, capacidad del proyecto, estado (`implemented`, `pending`, `verified`), script/archivo, endpoint/página, reporte/prueba, limitación y responsable. Diferenciar implementación de verificación. Cubrir explícitamente:

- Semana 7: problema, objetivos, preguntas, KPIs, datasets, diccionario, EDA, calidad y metodología. Cada KPI lleva fórmula, unidad, población/periodo y evidencia; no confundir una métrica de entrenamiento con un beneficio de negocio observado.
- Semana 10: datos procesados, variables, asociaciones, prototipo y resultados.
- Semana 13: clustering, series, grafos, **regresión numérica independiente** y comparación.
- Semana 16: web/dashboard, clasificación, textos, explicabilidad, monitoreo, documentación y sustentación.
- Sección 24: mecanismos de mantenimiento documentados; enlazar GER-02 si se implementa y la guía de mantenimiento disponible sin presentar un historial futuro como existente.
- Tecnologías sugeridas y producto de ejemplo: registrar adaptación al dominio financiero; no convertir Docker, React, SQL o deep learning en requisitos técnicos obligatorios.

Actualizar guion final con un caso por técnica y resultados reales, incluidos resultados desfavorables. Consolidar informe/presentación con aportes de los seis; si se crean o editan DOCX/PPTX, el agente debe aplicar las habilidades correspondientes y verificar renderizado. Este encargo define el contenido, no autoriza inventar resultados o aceptación del docente.

**Aceptación global de Angel:** navegación coherente, verificador que exige P0/P1, contratos centrales probados, matriz sin capacidades ficticias y revisión NLP preparada/confirmada según evidencia. La sustentación y firma humana permanecen acciones del equipo.
