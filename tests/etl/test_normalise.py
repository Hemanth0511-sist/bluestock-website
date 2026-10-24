import pytest

from src.etl.normalizer import normalize_year


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Mar-23", "2023-03"),
        ("Mar 23", "2023-03"),
        ("March-2023", "2023-03"),
        ("March 2023", "2023-03"),
        ("2023", "2023-03"),
        ("FY23", "2023-03"),
        ("FY2023", "2023-03"),
        ("Dec-22", "2022-12"),
        ("Dec 22", "2022-12"),
        ("December-2022", "2022-12"),
        ("Jun-23", "2023-06"),
        ("Jun 23", "2023-06"),
        ("June-2023", "2023-06"),
        ("2023-03", "2023-03"),
        ("2022-12", "2022-12"),
        ("  Mar-23  ", "2023-03"),
        ("mar-23", "2023-03"),
        ("FY24", "2024-03"),
        ("garbage", "PARSE_ERROR"),
        (None, None),
    ],
)
def test_normalize_year_variants(raw, expected):
    """Test normalize_year formats and edge cases."""
    assert normalize_year(raw) == expected
