from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
VALIDATOR = ROOT / "scripts" / "validate_model_card.py"
TEMPLATE = ROOT / "tests" / "fixtures" / "model_card_template.md"


def run_gate(
    card: Path, project_root: Path, *, require_c5: bool = False
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(VALIDATOR),
        str(card),
        "--project-root",
        str(project_root),
    ]
    if require_c5:
        command.append("--require-c5")
    return subprocess.run(command, check=False, capture_output=True, text=True)


def test_template_passes_structure_but_keeps_c5_not_ready() -> None:
    result = run_gate(TEMPLATE, ROOT)
    assert result.returncode == 0, result.stderr
    assert "STRUCTURE=PASS" in result.stdout
    assert "C5_EVIDENCE=NOT_READY" in result.stdout


def test_strict_c5_rejects_the_unmeasured_template() -> None:
    result = run_gate(TEMPLATE, ROOT, require_c5=True)
    assert result.returncode == 2
    assert "C5_PREUVES_REELLES_INCOMPLETES" in result.stderr


def test_strict_c5_accepts_measured_fields_with_local_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    run_id = "0123456789abcdef0123456789abcdef"
    for filename, content in {
        "artifact.txt": "model=rf.joblib version=0.1.0",
        "data.txt": "split=temporel sha256=abc",
        "metrics.txt": "pr_auc=mesuree threshold=mesure",
        "mlflow.txt": f"run_id={run_id}",
    }.items():
        (evidence / filename).write_text(content, encoding="utf-8")

    card = tmp_path / "model_card.md"
    card.write_text(
        TEMPLATE.read_text(encoding="utf-8")
        .replace(
            "Artefact et version : [à produire]",
            "Artefact et version : [mesuré] preuve=evidence/artifact.txt",
        )
        .replace(
            "Données, split temporel et empreinte : [à produire]",
            "Données, split temporel et empreinte : [mesuré] preuve=evidence/data.txt",
        )
        .replace(
            "Métriques et seuil : [à produire]",
            "Métriques et seuil : [mesuré] preuve=evidence/metrics.txt",
        )
        .replace(
            "MLflow run_id : [à produire]",
            f"MLflow run_id : [mesuré] {run_id} preuve=evidence/mlflow.txt",
        ),
        encoding="utf-8",
    )

    result = run_gate(card, tmp_path, require_c5=True)
    assert result.returncode == 0, result.stderr
    assert "C5_EVIDENCE=READY_FOR_REVIEW" in result.stdout


def test_marine_value_outside_benchmark_section_is_rejected(tmp_path: Path) -> None:
    card = tmp_path / "model_card.md"
    card.write_text(
        TEMPLATE.read_text(encoding="utf-8").replace(
            "Finalité et utilisateurs : [à produire]",
            "Finalité et utilisateurs : [à produire] seuil 0,41",
        ),
        encoding="utf-8",
    )
    result = run_gate(card, tmp_path)
    assert result.returncode == 2
    assert "BENCHMARK_MARINE_HORS_SECTION_4" in result.stderr
