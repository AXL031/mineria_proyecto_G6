# Inventario de datasets locales

Estos archivos fueron aportados por el equipo y se guardan en `data/bronze/` sin modificar su contenido. **No están versionados en Git.** La procedencia exacta, versión y condiciones de uso de cada copia deben confirmarse antes de publicar muestras o resultados.

| Dominio | Archivo local | Tamaño (bytes) | SHA-256 |
| --- | --- | ---: | --- |
| Transacciones | `data/bronze/transactions/PS_20174392719_1491204439457_log.csv` | 493534783 | `16910F90577B0D981BF8FF289714510BB89BC71BFF7D3F220F024E287E4EEA6B` |
| Crédito | `data/bronze/credit/credit_risk_dataset.csv` | 1804682 | `CE3C6D2167717BF1627D1C0C81CBCCD28323CD4AA7B96D542599366D5FF6AAC8` |
| Reclamos | `data/bronze/complaints/consumer_complaints.csv` | 175385569 | `DF219BBCF0E8233F33EB83454EF9B3451ADF471DB29618ACFB36D2DACC40ED3F` |

## Esquemas observados en la cabecera

### Transacciones

`step`, `type`, `amount`, `nameOrig`, `oldbalanceOrg`, `newbalanceOrig`, `nameDest`, `oldbalanceDest`, `newbalanceDest`, `isFraud`, `isFlaggedFraud`.

La estructura coincide con el formato conocido como PaySim y permite explorar transacciones y relaciones origen → destino. `step` es un paso de simulación, no una fecha calendario. La etiqueta `isFraud` requiere verificar su distribución antes de definir evaluación. No usar `isFlaggedFraud` como predictor sin comprobar su origen y disponibilidad al momento de la operación.

### Crédito

`person_age`, `person_income`, `person_home_ownership`, `person_emp_length`, `loan_intent`, `loan_grade`, `loan_amnt`, `loan_int_rate`, `loan_status`, `loan_percent_income`, `cb_person_default_on_file`, `cb_person_cred_hist_length`.

Este archivo **no tiene el esquema de Home Credit**. Tampoco contiene una clave de cliente o fecha en su cabecera. Hay que confirmar el significado de `loan_status` y revisar si variables como `loan_grade` o `loan_int_rate` están disponibles en el momento en que se pretende predecir.

### Reclamos

`date_received`, `product`, `sub_product`, `issue`, `sub_issue`, `consumer_complaint_narrative`, `company_public_response`, `company`, `state`, `zipcode`, `tags`, `consumer_consent_provided`, `submitted_via`, `date_sent_to_company`, `company_response_to_consumer`, `timely_response`, `consumer_disputed?`, `complaint_id`.

El archivo incluye una columna de texto, pero la primera fila observada la tiene vacía. Antes del módulo NLP hay que medir cobertura, longitud y condiciones de uso de las narrativas. `complaint_id` identifica reclamos; no une este archivo con los otros dos.

## Reglas para el equipo

1. Mantener los originales inmutables en Bronze. Cualquier limpieza va a Silver.
2. Registrar la URL o institución de origen, fecha de obtención y licencia de cada archivo en esta página cuando se confirmen.
3. Usar las huellas SHA-256 para verificar que todos procesan la misma versión.
4. Compartir los CSV mediante un medio acordado por el equipo. Un clon de Git contiene la estructura, no los datos.
