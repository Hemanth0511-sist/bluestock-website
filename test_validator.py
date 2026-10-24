import pytest

from src.analysis.validator import FinancialValidator


# ==========================================================
# is_valid_number() TESTS
# ==========================================================

def test_valid_number_integer():
    assert FinancialValidator.is_valid_number(100) is True


def test_valid_number_float():
    assert FinancialValidator.is_valid_number(12.5) is True


def test_valid_number_zero():
    assert FinancialValidator.is_valid_number(0) is True


def test_invalid_number_none():
    assert FinancialValidator.is_valid_number(None) is False


def test_invalid_number_string():
    assert FinancialValidator.is_valid_number("100") is False


# ==========================================================
# is_positive() TESTS
# ==========================================================

def test_positive_number():
    assert FinancialValidator.is_positive(50) is True


def test_positive_float():
    assert FinancialValidator.is_positive(12.5) is True


def test_zero_is_not_positive():
    assert FinancialValidator.is_positive(0) is False


def test_negative_number_is_not_positive():
    assert FinancialValidator.is_positive(-20) is False


# ==========================================================
# validate_ratio() TESTS
# ==========================================================

def test_valid_ratio_integer():
    assert FinancialValidator.validate_ratio(10) is True


def test_valid_ratio_float():
    assert FinancialValidator.validate_ratio(12.5) is True


def test_valid_ratio_zero():
    assert FinancialValidator.validate_ratio(0) is True


def test_invalid_ratio_none():
    assert FinancialValidator.validate_ratio(None) is False


def test_invalid_ratio_string():
    assert FinancialValidator.validate_ratio("12.5") is False