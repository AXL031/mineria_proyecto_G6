# Patrones descriptivos de fraude — Cueva

Reglas predefinidas sobre tipo, monto y saldo anterior. No modifican el modelo ni su umbral.
No se eligieron reglas por sus resultados en prueba. Son asociaciones retrospectivas, no causas ni atribuciones.

Modelo SHA-256: `e4d706ea530841d38a4964f275905cfe87c3e71d4db4ea509c973272de3abdb4`.
Silver SHA-256: `47c786d91fd92d81842bbd83bba86b5d39fc94f43f9928315884c6e118c2e46c`.

Soporte = operaciones que cumplen la regla / operaciones de la partición; confianza = fraudes entre las coincidencias; lift = confianza / prevalencia; cobertura = fraudes coincidentes / fraudes de la partición.
Las reglas se solapan: sus conteos y coberturas no se suman. Sin coincidencias, confianza/lift se muestran como N/D.

## train

Filas: 4,463,587; fraudes: 3,643; prevalencia: 0.081616%.

| Regla | Coincidencias | Fraudes | Soporte | Confianza | Lift | Cobertura |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Tipo TRANSFER | 369,248 | 1,812 | 8.2724% | 0.4907% | 6.01 | 49.7392% |
| Tipo CASH_OUT | 1,582,647 | 1,831 | 35.4568% | 0.1157% | 1.42 | 50.2608% |
| Monto positivo igual al saldo anterior | 3,567 | 3,567 | 0.0799% | 100.0000% | 1225.25 | 97.9138% |
| Monto supera el saldo anterior | 2,853,163 | 29 | 63.9209% | 0.0010% | 0.01 | 0.7960% |
| TRANSFER con monto positivo igual al saldo anterior | 1,764 | 1,764 | 0.0395% | 100.0000% | 1225.25 | 48.4216% |
| CASH_OUT con monto positivo igual al saldo anterior | 1,803 | 1,803 | 0.0404% | 100.0000% | 1225.25 | 49.4922% |

## validation

Filas: 980,416; fraudes: 564; prevalencia: 0.057527%.

| Regla | Coincidencias | Fraudes | Soporte | Confianza | Lift | Cobertura |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Tipo TRANSFER | 83,440 | 282 | 8.5107% | 0.3380% | 5.87 | 50.0000% |
| Tipo CASH_OUT | 344,551 | 282 | 35.1433% | 0.0818% | 1.42 | 50.0000% |
| Monto positivo igual al saldo anterior | 559 | 559 | 0.0570% | 100.0000% | 1738.33 | 99.1135% |
| Monto supera el saldo anterior | 644,276 | 0 | 65.7146% | 0.0000% | 0.00 | 0.0000% |
| TRANSFER con monto positivo igual al saldo anterior | 277 | 277 | 0.0283% | 100.0000% | 1738.33 | 49.1135% |
| CASH_OUT con monto positivo igual al saldo anterior | 282 | 282 | 0.0288% | 100.0000% | 1738.33 | 50.0000% |

## test

Filas: 918,617; fraudes: 4,006; prevalencia: 0.436090%.

| Regla | Coincidencias | Fraudes | Soporte | Confianza | Lift | Cobertura |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Tipo TRANSFER | 80,221 | 2,003 | 8.7328% | 2.4969% | 5.73 | 50.0000% |
| Tipo CASH_OUT | 310,302 | 2,003 | 33.7793% | 0.6455% | 1.48 | 50.0000% |
| Monto positivo igual al saldo anterior | 3,892 | 3,892 | 0.4237% | 100.0000% | 229.31 | 97.1543% |
| Monto supera el saldo anterior | 581,641 | 0 | 63.3170% | 0.0000% | 0.00 | 0.0000% |
| TRANSFER con monto positivo igual al saldo anterior | 1,902 | 1,902 | 0.2071% | 100.0000% | 229.31 | 47.4788% |
| CASH_OUT con monto positivo igual al saldo anterior | 1,990 | 1,990 | 0.2166% | 100.0000% | 229.31 | 49.6755% |

## Límites

PaySim es una simulación. La igualdad exacta de saldos no debe extrapolarse a otros sistemas o monedas. Las reglas no sustituyen el clasificador y no garantizan fraude en una operación individual. Revisar reglas nuevas con entrenamiento/validación y una evaluación nueva independiente.
