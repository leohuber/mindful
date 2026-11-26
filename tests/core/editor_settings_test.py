import pytest

from mindful.core.editor_settings import DEFAULT_FIELD_FONT_SIZE, resolve_field_font_size


@pytest.mark.parametrize("size", [8, 16, 48])
def test_configured_font_size_in_range_is_used(size: int) -> None:
    assert resolve_field_font_size({"field_font_size": size}) == size


@pytest.mark.parametrize(
    "config",
    [None, {}, {"field_font_size": 7}, {"field_font_size": 49}, {"field_font_size": "16"}, {"field_font_size": 16.5}, {"field_font_size": True}],
)
def test_missing_or_invalid_font_size_falls_back_to_default(config: object) -> None:
    assert resolve_field_font_size(config) == DEFAULT_FIELD_FONT_SIZE
