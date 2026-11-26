"""Resolve editor appearance settings from the add-on configuration."""

DEFAULT_FIELD_FONT_SIZE = 14
MIN_FIELD_FONT_SIZE = 8
MAX_FIELD_FONT_SIZE = 48


def resolve_field_font_size(config: object) -> int:
    """Read the field editor font size from the add-on configuration.

    Returns:
        The configured point size, or the default when it is missing, not an integer, or outside the supported range.
    """
    value = config.get("field_font_size") if isinstance(config, dict) else None
    if isinstance(value, bool) or not isinstance(value, int):
        return DEFAULT_FIELD_FONT_SIZE
    return value if MIN_FIELD_FONT_SIZE <= value <= MAX_FIELD_FONT_SIZE else DEFAULT_FIELD_FONT_SIZE
