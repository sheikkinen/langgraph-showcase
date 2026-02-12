"""Tests for the calculator module, tagged with requirement markers."""

import sys
from pathlib import Path

import pytest

# Add src/ to path so calculator is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from calculator import add, mul, sub


# --- REQ-CALC-001: Addition ---


@pytest.mark.req("REQ-CALC-001")
def test_add_positive():
    assert add(2, 3) == 5


@pytest.mark.req("REQ-CALC-001")
def test_add_negative():
    assert add(-1, -2) == -3


@pytest.mark.req("REQ-CALC-001")
def test_add_zero():
    assert add(0, 0) == 0


# --- REQ-CALC-002: Subtraction ---


@pytest.mark.req("REQ-CALC-002")
def test_sub_positive():
    assert sub(5, 3) == 2


@pytest.mark.req("REQ-CALC-002")
def test_sub_negative_result():
    assert sub(1, 5) == -4


# --- REQ-CALC-003: Multiplication ---


@pytest.mark.req("REQ-CALC-003")
def test_mul_positive():
    assert mul(3, 4) == 12


@pytest.mark.req("REQ-CALC-003")
def test_mul_by_zero():
    assert mul(99, 0) == 0


# --- REQ-CALC-004: Error handling ---


@pytest.mark.req("REQ-CALC-004")
def test_add_rejects_string():
    with pytest.raises(TypeError):
        add("a", 1)


@pytest.mark.req("REQ-CALC-004")
def test_sub_rejects_none():
    with pytest.raises(TypeError):
        sub(None, 2)


@pytest.mark.req("REQ-CALC-001", "REQ-CALC-004")
def test_add_accepts_floats():
    assert add(1.5, 2.5) == 4.0
