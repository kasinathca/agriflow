from __future__ import annotations

import csv
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PPTX = ROOT / "deliverables" / "final_review" / "AgriFlow_Final_Review.pptx"
FORECAST = ROOT / "deliverables" / "final_review" / "forecasting"
REPORT = ROOT / "deliverables" / "final_review" / "verification_report.json"

NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
REQUIRED_HEADINGS = [
    "Problem Statement", "Objectives", "Proposed Solution and Architecture",
    "Dataset Description", "Data Preprocessing and Exploratory Analysis", "Methodology",
    "Model Implementation", "Evaluation Metrics", "Model Performance Comparison",
    "Prediction Results and Diagnostics", "Application and Demonstration",
    "Challenges, Solutions and Drawbacks", "Conclusion and Future Scope", "References",
]
METRICS = ["MAE", "MSE", "RMSE", "R-squared", "MAPE", "sMAPE", "WAPE", "Median AE", "Mean bias", "Directional accuracy"]


def slide_number(name: str) -> int:
    return int(re.search(r"slide(\d+)\.xml$", name).group(1))


def main() -> int:
    findings: list[str] = []
    if not PPTX.exists():
        raise SystemExit(f"Missing presentation: {PPTX}")
    with zipfile.ZipFile(PPTX) as archive:
        slide_names = sorted(
            [name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)],
            key=slide_number,
        )
        slide_texts = []
        for name in slide_names:
            root = ET.fromstring(archive.read(name))
            slide_texts.append(" ".join(node.text or "" for node in root.findall(".//a:t", NS)))
        combined = "\n".join(slide_texts)
        media = [name for name in archive.namelist() if name.startswith("ppt/media/")]
        charts = [name for name in archive.namelist() if re.fullmatch(r"ppt/(?:slides/)?charts/chart\d+\.xml", name)]
    if len(slide_names) != 15:
        findings.append(f"Expected 15 slides; found {len(slide_names)}")
    for heading in REQUIRED_HEADINGS:
        if heading not in combined:
            findings.append(f"Missing heading: {heading}")
    for metric in METRICS:
        if metric not in combined:
            findings.append(f"Missing metric label: {metric}")
    for identity in ["Kasinath C A", "24MID0124", "Kamal Nayan C S", "24MID0189"]:
        if identity not in combined:
            findings.append(f"Missing team identity: {identity}")
    if len(charts) < 6:
        findings.append(f"Expected at least 6 native charts; found {len(charts)}")
    if not media:
        findings.append("No embedded media found")
    with (FORECAST / "model_comparison.csv").open(newline="", encoding="utf-8") as handle:
        comparison = list(csv.DictReader(handle))
    metadata = json.loads((FORECAST / "selected_model.json").read_text(encoding="utf-8"))
    selected = next(row for row in comparison if row["model"] == metadata["selected_model"])
    expected_claims = [
        metadata["selected_model"],
        f"{float(metadata['selected_validation_mae']):.1f}",
        f"{float(selected['mae']):.1f}",
        f"{float(selected['rmse']):.1f}",
        f"{float(metadata['mae_improvement_vs_persistence_pct']):.1f}%",
    ]
    for claim in expected_claims:
        if claim not in combined:
            findings.append(f"Saved metric/model claim missing from deck: {claim}")
    placeholder_markers = ["TODO", "TBD", "PLACEHOLDER", "INSERT "]
    for marker in placeholder_markers:
        if marker in combined.upper():
            findings.append(f"Unsupported placeholder marker: {marker}")
    report = {
        "status": "PASS" if not findings else "FAIL",
        "presentation": str(PPTX.relative_to(ROOT)),
        "slide_count": len(slide_names),
        "native_chart_count": len(charts),
        "embedded_media_count": len(media),
        "required_headings_present": not any(item.startswith("Missing heading") for item in findings),
        "ten_metric_labels_present": not any(item.startswith("Missing metric") for item in findings),
        "team_identity_present": not any(item.startswith("Missing team") for item in findings),
        "saved_claims_match": not any(item.startswith("Saved metric/model") for item in findings),
        "findings": findings,
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if not findings else 1


if __name__ == "__main__":
    sys.exit(main())
