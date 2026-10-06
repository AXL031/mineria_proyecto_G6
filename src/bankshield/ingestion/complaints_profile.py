"""Perfilado de Consumer Complaints (CFPB) en memoria acotada; no transforma Bronze."""

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

FIELDS = (
    "date_received",
    "product",
    "sub_product",
    "issue",
    "sub_issue",
    "consumer_complaint_narrative",
    "company_public_response",
    "company",
    "state",
    "zipcode",
    "tags",
    "consumer_consent_provided",
    "submitted_via",
    "date_sent_to_company",
    "company_response_to_consumer",
    "timely_response",
    "consumer_disputed?",
    "complaint_id",
)


def compute_sha256(path: Path) -> str:
    """Calcula el hash SHA-256 del archivo en bloques."""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def extract_year(date_str: str) -> str:
    """Extrae el año desde formatos comunes como MM/DD/YYYY o YYYY-MM-DD."""
    date_str = date_str.strip()
    if not date_str:
        return "desconocido"
    if "/" in date_str:
        parts = date_str.split("/")
        if len(parts) == 3 and len(parts[2]) == 4:
            return parts[2]
    elif "-" in date_str:
        parts = date_str.split("-")
        if len(parts) >= 1 and len(parts[0]) == 4:
            return parts[0]
    return "otro"


def profile_complaints(path: Path | str, limit: int | None = None) -> dict:
    """Perfilar archivo CSV de reclamos respetando límites de memoria."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")
    if limit is not None and limit <= 0:
        raise ValueError("El límite debe ser un entero positivo")

    sha256 = compute_sha256(path)

    total_rows = 0
    valid_rows = 0
    invalid_rows = 0

    missing_by_column = {field: 0 for field in FIELDS}
    issues = Counter()

    # Métricas de narrativas
    narrative_count = 0
    total_narrative_chars = 0
    total_narrative_words = 0
    min_narrative_chars = math.inf
    max_narrative_chars = 0
    narratives_with_redaction = 0

    # Contadores categóricos
    product_counter = Counter()
    product_with_narrative_counter = Counter()
    company_counter = Counter()
    issue_counter = Counter()
    sub_product_counter = Counter()
    submitted_via_counter = Counter()
    disputed_counter = Counter()
    year_counter = Counter()

    seen_ids = set()
    duplicate_ids = 0
    min_date = None
    max_date = None

    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("El archivo está vacío o no tiene cabecera válida")
        
        # Validar cabecera esperada
        header_diff = set(FIELDS) - set(reader.fieldnames)
        if header_diff:
            raise ValueError(f"Cabecera incompleta; faltan campos: {header_diff}")

        for row in reader:
            total_rows += 1

            row_issues = []
            if None in row:
                row_issues.append("extra_columns")

            # Revisión de nulos o vacíos
            for field in FIELDS:
                val = row.get(field)
                if val is None or not str(val).strip():
                    missing_by_column[field] += 1

            # Validación de identificador único
            cid_str = row.get("complaint_id", "").strip()
            if not cid_str:
                row_issues.append("missing:complaint_id")
            else:
                try:
                    cid = int(cid_str)
                    if cid in seen_ids:
                        duplicate_ids += 1
                    else:
                        seen_ids.add(cid)
                except ValueError:
                    row_issues.append("invalid:complaint_id")

            # Validación de fecha y producto obligatorios
            date_val = row.get("date_received", "").strip()
            prod_val = row.get("product", "").strip()
            if not date_val:
                row_issues.append("missing:date_received")
            if not prod_val:
                row_issues.append("missing:product")

            if row_issues:
                invalid_rows += 1
                for issue in row_issues:
                    issues[issue] += 1
            else:
                valid_rows += 1

                # Métricas de narrativa
                narrative = row.get("consumer_complaint_narrative", "").strip()
                if narrative:
                    narrative_count += 1
                    char_len = len(narrative)
                    word_len = len(narrative.split())
                    total_narrative_chars += char_len
                    total_narrative_words += word_len
                    if char_len < min_narrative_chars:
                        min_narrative_chars = char_len
                    if char_len > max_narrative_chars:
                        max_narrative_chars = char_len
                    if "XXXX" in narrative:
                        narratives_with_redaction += 1
                    product_with_narrative_counter[prod_val] += 1

                # Métricas categóricas
                product_counter[prod_val] += 1
                company = row.get("company", "").strip()
                if company:
                    company_counter[company] += 1
                issue = row.get("issue", "").strip()
                if issue:
                    issue_counter[issue] += 1
                sub_prod = row.get("sub_product", "").strip()
                if sub_prod:
                    sub_product_counter[sub_prod] += 1
                submitted_via = row.get("submitted_via", "").strip()
                if submitted_via:
                    submitted_via_counter[submitted_via] += 1
                disputed = row.get("consumer_disputed?", "").strip()
                if disputed:
                    disputed_counter[disputed] += 1

                year = extract_year(date_val)
                year_counter[year] += 1

                if min_date is None or date_val < min_date:
                    min_date = date_val
                if max_date is None or date_val > max_date:
                    max_date = date_val

            if limit is not None and total_rows >= limit:
                break

    scope = "first_rows_sample" if (limit is not None and total_rows == limit) else "complete_file"

    avg_chars = round(total_narrative_chars / narrative_count, 2) if narrative_count else 0.0
    avg_words = round(total_narrative_words / narrative_count, 2) if narrative_count else 0.0
    narrative_rate = round(narrative_count / valid_rows, 6) if valid_rows else 0.0
    redaction_rate = round(narratives_with_redaction / narrative_count, 6) if narrative_count else 0.0

    by_product = {}
    for prod, count in product_counter.most_common():
        with_narrative = product_with_narrative_counter.get(prod, 0)
        by_product[prod] = {
            "rows": count,
            "percentage": round(count / valid_rows, 6) if valid_rows else 0.0,
            "narratives": with_narrative,
            "narrative_coverage": round(with_narrative / count, 6) if count else 0.0,
        }

    return {
        "source": {
            "file": path.name,
            "sha256": sha256,
            "path": str(path),
        },
        "scope": scope,
        "rows": total_rows,
        "valid_rows": valid_rows,
        "invalid_rows": invalid_rows,
        "duplicate_complaint_ids": duplicate_ids,
        "issues": dict(issues),
        "missing_by_column": missing_by_column,
        "narrative_metrics": {
            "count": narrative_count,
            "coverage_rate": narrative_rate,
            "min_chars": int(min_narrative_chars) if narrative_count else 0,
            "max_chars": int(max_narrative_chars),
            "avg_chars": avg_chars,
            "avg_words": avg_words,
            "narratives_with_redaction": narratives_with_redaction,
            "redaction_rate": redaction_rate,
        },
        "by_product": by_product,
        "top_companies": dict(company_counter.most_common(10)),
        "top_issues": dict(issue_counter.most_common(10)),
        "top_sub_products": dict(sub_product_counter.most_common(10)),
        "submitted_via": dict(submitted_via_counter.most_common()),
        "disputed_distribution": dict(disputed_counter.most_common()),
        "by_year": dict(sorted(year_counter.items())),
        "temporal_range": {
            "min_date": min_date,
            "max_date": max_date,
        },
    }


def write_reports(profile: dict, json_path: Path | str, markdown_path: Path | str | None = None) -> None:
    """Escribe informe JSON y opcionalmente Markdown."""
    json_path = Path(json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")

    if markdown_path:
        nm = profile["narrative_metrics"]
        lines = [
            "# Perfil de Reclamos de Clientes — Módulo NLP",
            "",
            "Informe generado por `scripts/profile_complaints.py`. Los originales en Bronze no se modifican.",
            "",
            f"- **Archivo:** `{profile['source']['file']}`",
            f"- **SHA-256:** `{profile['source']['sha256']}`",
            f"- **Alcance:** `{profile['scope']}`; registros analizados: {profile['rows']:,}",
            f"- **Registros válidos:** {profile['valid_rows']:,}; **inválidos:** {profile['invalid_rows']:,}",
            f"- **Identificadores duplicados (`complaint_id`):** {profile['duplicate_complaint_ids']:,}",
            "",
            "## 1. Cobertura de Narrativas de Texto",
            "",
            f"- **Reclamos con narrativa de texto:** {nm['count']:,} ({nm['coverage_rate']:.2%})",
            f"- **Reclamos sin texto (solo estructurados):** {profile['valid_rows'] - nm['count']:,} ({1 - nm['coverage_rate']:.2%})",
            f"- **Longitud promedio en caracteres:** {nm['avg_chars']:,} (Mín: {nm['min_chars']}, Máx: {nm['max_chars']:,})",
            f"- **Longitud promedio en palabras:** {nm['avg_words']:,} palabras por relato",
            f"- **Relatos con marcas de anonimización (`XXXX`):** {nm['narratives_with_redaction']:,} ({nm['redaction_rate']:.2%})",
            "",
            "> **Hallazgo clave de NLP:** Solo una fracción de los reclamos incluye narrativa libre del consumidor. "
            "El preprocesamiento debe limpiar y manejar específicamente los tokens de censura `XXXX` / fechas censuradas.",
            "",
            "## 2. Distribución y Cobertura por Producto Financiero",
            "",
            "| Producto | Reclamos Totales | % del Total | Con Narrativa | % Cobertura Texto |",
            "| :--- | ---: | ---: | ---: | ---: |",
        ]
        for prod, data in profile["by_product"].items():
            lines.append(
                f"| {prod} | {data['rows']:,} | {data['percentage']:.2%} | "
                f"{data['narratives']:,} | {data['narrative_coverage']:.2%} |"
            )

        lines += [
            "",
            "## 3. Calidad y Valores Ausentes por Columna",
            "",
            "| Columna | Valores Ausentes | % Ausente |",
            "| :--- | ---: | ---: |",
        ]
        for field, count in profile["missing_by_column"].items():
            pct = count / profile["rows"] if profile["rows"] else 0.0
            lines.append(f"| `{field}` | {count:,} | {pct:.2%} |")

        lines += [
            "",
            f"**Incidencias de validación:** `{json.dumps(profile['issues'], ensure_ascii=False)}`",
            "",
            "## 4. Cobertura Temporal y Tendencias",
            "",
            f"- **Fecha más antigua registrada:** `{profile['temporal_range']['min_date']}`",
            f"- **Fecha más reciente registrada:** `{profile['temporal_range']['max_date']}`",
            "",
            "### Reclamos por Año",
            "",
            "| Año | Cantidad de Reclamos |",
            "| :--- | ---: |",
        ]
        for yr, cnt in profile["by_year"].items():
            lines.append(f"| {yr} | {cnt:,} |")

        lines += [
            "",
            "## 5. Principales Causas y Empresas Involucradas",
            "",
            "### Top 10 Motivos de Queja (`issue`)",
            "",
            "| Motivo (`issue`) | Frecuencia |",
            "| :--- | ---: |",
        ]
        for iss, cnt in profile["top_issues"].items():
            lines.append(f"| {iss} | {cnt:,} |")

        lines += [
            "",
            "### Top 10 Compañías con más Quejas",
            "",
            "| Compañía | Frecuencia |",
            "| :--- | ---: |",
        ]
        for comp, cnt in profile["top_companies"].items():
            lines.append(f"| {comp} | {cnt:,} |")

        lines += [
            "",
            "## 6. Conclusiones y Próximos Pasos para el Módulo NLP",
            "",
            "1. **Estrategia dual:** Desarrollar tanto un análisis estructurado (tendencias temporales, productos, empresas) "
            "como un pipeline de NLP enfocado exclusivamente en el subconjunto de reclamos con narrativa.",
            "2. **Limpieza de texto especializada:** Implementar una normalización que remueva ruido administrativo (`XXXX`, fechas censuradas, saltos de línea repetidos) y conserve términos financieros clave.",
            "3. **Modelado NLP:** Línea base con TF-IDF + Clasificador supervisado (ej. predecir `product` a partir del texto de la queja) y extracción no supervisada de tópicos (NMF / LDA) para descubrir motivos ocultos de insatisfacción.",
            "4. **Propuesta de Panel:** Una vista interactiva con KPIs globales, buscador semántico o de texto, tendencias temporales y explorador de quejas reales anonimizadas.",
        ]

        markdown_path = Path(markdown_path)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
