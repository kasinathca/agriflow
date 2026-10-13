from pathlib import Path

import pytest


def test_final_presentation_exists_and_passes_structural_validation():
    root = Path(__file__).resolve().parents[1]
    pptx = root / "deliverables" / "final_review" / "AgriFlow_Final_Review.pptx"
    if not pptx.exists():
        pytest.skip("Generate the final presentation before running the release validation test.")
    from scripts.validate_final_presentation import main

    assert main() == 0
