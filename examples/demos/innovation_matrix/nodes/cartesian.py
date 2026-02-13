"""Cartesian product tool for Innovation Matrix.

Creates 25 capability × constraint pairs from the dimensions.
"""

from itertools import product


def cartesian_product(state: dict) -> dict:
    """Generate all 25 capability × constraint pairs.

    Args:
        state: Must contain 'dimensions' with 'capabilities' and 'constraints' lists
               (dimensions can be dict or Pydantic model)

    Returns:
        dict with 'pairs' list of {capability, constraint, id} dicts
    """
    dimensions = state.get("dimensions", {})

    # Handle both dict and Pydantic model access
    if hasattr(dimensions, "capabilities"):
        capabilities = dimensions.capabilities
        constraints = dimensions.constraints
    else:
        capabilities = dimensions.get("capabilities", [])
        constraints = dimensions.get("constraints", [])

    pairs = []
    for i, (cap, con) in enumerate(product(capabilities, constraints)):
        pairs.append(
            {
                "id": f"C{i // 5 + 1}S{i % 5 + 1}",
                "capability": cap,
                "constraint": con,
            }
        )

    return {"pairs": pairs}
