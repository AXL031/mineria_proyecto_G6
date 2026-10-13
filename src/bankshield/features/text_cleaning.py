"""Limpieza neutral de narrativas CFPB: sustituye la censura por marcadores y normaliza espacios.

No elimina stopwords ni aplica stemming: eso corresponde al vectorizador del modelo, que debe
ajustarse solo con entrenamiento.
"""

import re

DATE_MARKER = "<fecha>"
AMOUNT_MARKER = "<monto>"
REDACTED_MARKER = "<censurado>"
MARKERS = (DATE_MARKER, AMOUNT_MARKER, REDACTED_MARKER)

# Monto anonimizado por la CFPB, p. ej. {$27.00} o {$1,250.50}.
_AMOUNT = re.compile(r"\{\$[\d,]*\.?\d+\}")
# Fecha con componentes censurados, p. ej. XX/XX/XXXX, XXXX/XXXX/2015, XX/XX/15.
_DATE = re.compile(r"(?<![\w/])[X\d]{2,4}/[X\d]{2,4}/[X\d]{2,4}(?![\w/])")
# Racha de X que no forma parte de una palabra normal (XXXX, XXXXXXXX, XXXXI). Incluye las x en
# minúscula con que los propios consumidores ocultan números de cuenta (xxxxxxxxxxx).
_REDACTED = re.compile(r"(?<![A-Za-z])[Xx]{2,}(?![a-z])")
_WHITESPACE = re.compile(r"\s+")
# Racha de x que sobrevive en el texto ya limpio y en minúsculas.
RESIDUAL_REDACTION = re.compile(r"(?<![a-z])x{2,}(?![a-z])")


def _mask_date(match: re.Match) -> str:
    # Una fecha sin ninguna X es un dato visible, no censura: se deja intacta.
    return DATE_MARKER if "X" in match.group(0) else match.group(0)


def mask_redactions(text: str) -> tuple[str, int]:
    """Devuelve el texto con marcadores y el número de elementos censurados reemplazados."""
    count = 0

    def replace(marker, fn=None):
        def inner(match):
            nonlocal count
            value = fn(match) if fn else marker
            if value != match.group(0):
                count += 1
            return value
        return inner

    text = _AMOUNT.sub(replace(AMOUNT_MARKER), text)
    text = _DATE.sub(replace(None, _mask_date), text)
    text = _REDACTED.sub(replace(REDACTED_MARKER), text)
    return text, count


def clean_narrative(text: str | None) -> str:
    """Minúsculas, censura como marcadores y espacios/saltos de línea colapsados."""
    if text is None:
        return ""
    masked, _ = mask_redactions(str(text))
    return _WHITESPACE.sub(" ", masked).strip().lower()


def count_redactions(text: str | None) -> int:
    """Cantidad de fechas, montos y rachas censuradas presentes en el texto original."""
    if text is None:
        return 0
    return mask_redactions(str(text))[1]
