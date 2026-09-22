"""
Maps ParsedRequirement JSON keys to labels and formatted values.

Not generic by design -- tightly coupled to ParsedRequirement in src/llms/schemas.py.
Update this file whenever ParsedRequirement fields change.
"""

_KNOWN_KEYS = {"requirement_summary", "parameters"}


def map_card(card: dict) -> list[tuple[str, str]]:
    """Convert a raw ParsedRequirement dict to display rows.

    Always includes requirement_summary.
    Adds one value row per parameter that has both value and unit.
    """
    result = [
        ("Popis", str(card.get("requirement_summary", ""))),
    ]

    for param in card.get("parameters", []):
        if isinstance(param, dict):
            value = param.get("parameter_value")
            unit = param.get("parameter_unit")
        else:
            value = param.parameter_value
            unit = param.parameter_unit
        if value is not None and unit is not None:
            result.append(("Hodnota", f"{value} {unit}"))

    # Pass through unexpected keys not in the schema (future-proofing)
    for key, raw in card.items():
        if key not in _KNOWN_KEYS and raw is not None:
            result.append((key, str(raw)))

    return result
