# Revisión de Taco — flujo de preparación y reproducción de GER-01

Revisión técnica del 9 de noviembre de 2026 sobre `main` (`de6bbe2`). La pidió
el [encargo de Gerardo](encargos/gerardo.md) («Taco revisa el flujo») y la
registra la fila de Gerardo en [pendientes y contratos](pendientes-cierre-2026-10-20.md).

> **Alcance de la firma.** Este documento reúne evidencia técnica preparada a
> solicitud de Taco. No atribuye a Gerardo, a Sevan ni a una segunda persona una
> aceptación que todavía no se haya registrado. La revisión humana cruzada, la
> comprobación de versiones/modelos por Sevan y la reproducción en otra PC
> siguen pendientes.

## Qué se revisó

| Componente | Revisión |
| --- | --- |
| DAG y dependencias | `scripts/prepare_demo.py`: 14 etapas ejecutables, orden y dependencias de cada una. |
| Contrato de la etapa D1 | Entradas, configuración, fuentes y salidas declaradas para `analytics-d1`. |
| Validación de recibos y salidas | `src/bankshield/preparation.py`: firma, reuso, `--force`, manifiesto y publicación atómica. |
| Protecciones | Rutas fuera del proyecto, Bronze y documentación versionada como salidas. |
| Documentación | `docs/ger-01-reproduccion.md` y `docs/pruebas-reproduccion.md` frente al código. |
| Reproducción de D1 | Corrida completa en rutas temporales con la misma configuración. |

## Evidencia ejecutada en este equipo

| Verificación | Resultado observado |
| --- | --- |
| `pip check` | Sin conflictos. |
| `prepare_demo.py --plan` | 14 etapas ejecutables; D1 depende de Silver; cuatro ampliaciones se listan con motivo (`CUE-01`, `SEV-01`, `RHA-01` fuera del alcance `current` y `GER-02` como P2). |
| `tests/unit/test_preparation.py` | 16 pruebas aprobadas. |
| Pruebas de datos y segmentos (`test_analytical_transactions`, `test_segments`, `test_api_segments`, `test_segments_dashboard`) | 49 pruebas aprobadas. |
| Suite completa (`unittest discover -s tests/unit`) | 328 pruebas aprobadas, 35.5 s. |
| Reproducción de D1 en rutas temporales | 6,362,620 filas de entrada y salida, 0 excluidas, nueve controles aprobados, 23.4 s. |

La reproducción usó `configs/analytics.json` con salidas redirigidas a
`artifacts/reports/revisiones-taco/`, para no tocar Silver, el mart, el Gold de
segmentos ni los reportes versionados. Resultado:

| Huella | Valor |
| --- | --- |
| Dataset D1 SHA-256 | `A4C6F55EC8DBB5351B8F2B6F5B8BE59E8C4C4696FBC4815F22B6CDC1234960EA` |
| Esquema de bins SHA-256 | `54685F5BDBA5360600B74E4539AB13FB76FAAE2BAD4D062A2CDB60EAB1AD9386` |
| Silver de origen SHA-256 | `47C786D91FD92D81842BBD83BBA86B5D39FC94F43F9928315884C6E118C2E46C` |

Las tres huellas coinciden con la entrega de TAC-01 y con lo publicado en el
[contrato analítico](transacciones/contrato-analitico.md).

## Contrato de la etapa `analytics-d1`

El DAG declara exactamente lo que el contrato de datos exige:

- Dependencia: `transactions-silver`.
- Entradas: `data/silver/transactions/transactions.parquet` y su reporte de calidad.
- Configuración: `configs/analytics.json`.
- Fuentes de código: `src/bankshield/transforms/analytical_transactions.py`.
- Salidas: el Parquet D1 y los dos reportes (`dataset.json`, `discretization.json`).
- `schema_version` exigida para ambos JSON: 1.

## Qué valida el preparador

1. **Firma del recibo:** receta (`recipe_sha256`), configuración canónica,
   huellas de las fuentes de código, huellas de las entradas y huella del
   entorno (Python, plataforma y paquetes instalados).
2. **Salidas publicadas:** huella y tamaño de cada salida declarada; los Parquet
   deben ser legibles y no vacíos.
3. **Contratos de los reportes:** `schema_version` esperada y que todo
   `quality_checks` sea `true`.
4. **Identidades cruzadas:** si el reporte publica `source`, `training_input` u
   `output` con `sha256`, ese valor debe coincidir con una entrada o salida
   declarada. En D1 esto vincula el reporte con el Silver de origen y con el
   Parquet generado.
5. **Reuso y `--force`:** solo reutiliza con recibo válido y salidas intactas;
   `--force` reconstruye la selección completa y sus dependencias, incluido fraude.
6. **Publicación:** manifiesto atómico con estado, tiempos, huellas, logs por
   corrida y error; se publica también cuando una etapa falla y los dependientes
   no se ejecutan.
7. **Protecciones:** rechaza rutas fuera del proyecto y salidas dentro de
   `data/bronze` o `docs`; no acepta restos de una corrida anterior cuando una
   etapa declara haber construido sus salidas; si una entrada, configuración o
   fuente cambia durante la ejecución, la corrida falla.

## Límites de esta revisión

- **No se verificó la corrida de Gerardo.** En este clon no existen
  `artifacts/reports/demo/`, sus recibos ni `reproduction-comparison.json`; no se
  puede confirmar su manifiesto ni sus tiempos sin esos artefactos. Esta revisión
  cubre código, documentación y una corrida propia de D1.
- **No se probó el reuso real de D1 en este clon.** El camino de reuso está
  cubierto por las 16 pruebas del preparador con etapas mínimas; demostrarlo con
  D1 exigiría una corrida completa de Silver para generar el recibo.
- **Invariantes de dominio:** el preparador valida contratos genéricos y
  coherencia de huellas, no recuentos por partición, cortes de bins ni ausencia
  de fuga. Eso queda cubierto por `tests/unit/test_analytical_transactions.py` y
  por la revisión de particiones que corresponde a Gerardo.
- **Rendimiento:** los tiempos observados describen este equipo y no son
  garantías para otra PC.

## Reproducir esta revisión

Se copia `configs/analytics.json` cambiando solo `output`, `dataset_report` y
`discretization_report` a una carpeta bajo `artifacts/`, y se ejecuta:

```powershell
.venv-pruebas/Scripts/python.exe scripts/build_analytics_transactions.py --config artifacts/reports/revisiones-taco/analytics-review.json
```

Después se comparan las huellas con `Get-FileHash` y con
`discretization.json`. No se usa `prepare_demo.py --stage analytics-d1` para esta
comprobación porque, sin recibos previos, ese comando reconstruiría también
Silver y otros derivados de la demo.

## Conclusión

Revisión técnica **favorable, sin objeciones bloqueantes** para el flujo de
preparación y reproducción de GER-01 en el alcance `current`. El DAG trata a D1
como una etapa con contrato verificable y la corrida propia reproduce las tres
huellas documentadas.

Siguen pendientes, por requerir personas y no ejecuciones:

- Revisión de versiones y modelos por Sevan.
- Revisión de particiones D1 por Gerardo y aceptación cruzada del contrato por Cueva.
- Confirmación de una segunda persona y reproducción en otra PC.
- Publicación de los commits y comprobación del CI correspondiente.
