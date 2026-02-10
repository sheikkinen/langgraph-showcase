"""Test that 'backward compatibility' markers are cleaned up in source code.

Per project guidelines (.github/copilot-instructions.md):
"Term 'backward compatibility' is a key indicator for a refactoring need."

This test fails if any Python source files contain backward compatibility markers,
ensuring deprecated code gets cleaned up rather than accumulating.
"""

import subprocess
from pathlib import Path

import pytest


class TestNoBackwardCompatibilityMarkers:
    """Ensure no backward compatibility markers exist in source code."""

    @pytest.mark.req("REQ-YG-034")
    def test_no_backward_compat_in_yamlgraph_source(self):
        """Source files should not contain 'backward compatibility' markers.

        Allowed exceptions:
        - deprecation.py: Documents the DeprecationError pattern
        - Tests in this file
        """
        project_root = Path(__file__).parent.parent.parent
        yamlgraph_dir = project_root / "yamlgraph"

        result = subprocess.run(
            [
                "grep",
                "-rn",
                "-i",
                "backward compatib",
                str(yamlgraph_dir),
                "--include=*.py",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:  # Found matches
            lines = result.stdout.strip().split("\n")
            # Filter out allowed files
            violations = [
                line
                for line in lines
                if "deprecation.py" not in line  # Pattern documentation
            ]

            if violations:
                msg = (
                    "Found 'backward compatibility' markers in source code.\n"
                    "Per guidelines, this signals refactoring need.\n"
                    "Clean up deprecated code or move to deprecation.py.\n\n"
                    "Violations:\n" + "\n".join(f"  {v}" for v in violations)
                )
                raise AssertionError(msg)
