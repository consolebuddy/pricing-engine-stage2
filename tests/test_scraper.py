from scraper_lib.utils import normalize_price, clean_text

def test_normalize_price_basic():
    assert normalize_price("19,90 €")[0] == 19.90
    assert normalize_price("€12")[0] == 12.0
    assert normalize_price("12.50 EUR") == (12.50, "EUR")

def test_clean_text():
    assert clean_text("  hello\nworld  ") == "hello world"