from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REPRODUCTION_SCRIPT = (
    PROJECT_ROOT
    / "examples"
    / "holdout_20260829_091754"
    / "reproduce_sample.py"
)


def test_public_holdout_reproduction() -> None:
    """
    Run the complete public raw-data reproduction example.

    The script itself verifies the frozen numerical reference result
    and the execution simulator's mechanical causality invariants.
    """
    result = subprocess.run(
        [
            sys.executable,
            str(REPRODUCTION_SCRIPT),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    output = result.stdout

    assert (
        "Completed trades:         78"
        in output
    )

    assert (
        "Long / short:             41 / 37"
        in output
    )

    assert (
        "Mean gross return:        "
        "+0.0458951523 bps/trade"
        in output
    )

    assert (
        "Mechanical validation:   PASS"
        in output
    )

    assert (
        "Reference-result check:  PASS"
        in output
    )
