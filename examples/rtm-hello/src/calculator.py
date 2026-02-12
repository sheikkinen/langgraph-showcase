"""A minimal calculator demonstrating TDD with Requirement Traceability."""


def add(a: float, b: float) -> float:
    """Add two numbers (REQ-CALC-001)."""
    _validate(a, b)
    return a + b


def sub(a: float, b: float) -> float:
    """Subtract b from a (REQ-CALC-002)."""
    _validate(a, b)
    return a - b


def mul(a: float, b: float) -> float:
    """Multiply two numbers (REQ-CALC-003)."""
    _validate(a, b)
    return a * b


def _validate(a: object, b: object) -> None:
    """Raise TypeError for non-numeric inputs (REQ-CALC-004)."""
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        raise TypeError(f"Expected numbers, got {type(a).__name__} and {type(b).__name__}")
