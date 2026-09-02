from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ALLOWED_STATUSES = {"mesure", "a produire", "non mesure", "a confirmer", "benchmark externe"}
REQUIRED_SECTIONS = {
    "niveau metier",
    "niveau technique / maintenance",
    "niveau conformite ai act",
}
C5_FIELDS = {
    "artefact et version",
    "donnees, split temporel et empreinte",
    "metriques et seuil",
    "mlflow run_id",
}
MARINE_MARKERS = ("0,41", "0.41", "0,62", "0.62", "16,6", "202,6", "612,8", "0,158", "0,352")
FIELD_RE = re.compile(r"^-\s*([^:]+):\s*\[([^]]+)]\s*(.*)$")
RUN_ID_RE = re.compile(r"\b(?:[0-9a-f]{32}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})\b", re.I)
PROOF_RE = re.compile(r"\bpreuve=([^\s;]+)")


def normalized(value: str) -> str:
    plain = unicodedata.normalize("NFKD", value)
    plain = "".join(char for char in plain if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", plain.strip().lower())


@dataclass(frozen=True)
class Field:
    section: str
    name: str
    status: str
    value: str
    line: int


def parse_card(text: str) -> tuple[set[str], list[Field]]:
    sections: set[str] = set()
    fields: list[Field] = []
    current = ""
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("## "):
            current = normalized(re.sub(r"^\d+\.\s*", "", line[3:]))
            sections.add(current)
            continue
        match = FIELD_RE.match(line)
        if match:
            fields.append(
                Field(
                    section=current,
                    name=normalized(match.group(1)),
                    status=normalized(match.group(2)),
                    value=match.group(3).strip(),
                    line=line_number,
                )
            )
    return sections, fields


def resolve_proof(project_root: Path, raw_path: str) -> Path | None:
    candidate = Path(raw_path.strip("\"'"))
    if candidate.is_absolute():
        return None
    resolved = (project_root / candidate).resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError:
        return None
    return resolved


def validate(card: Path, project_root: Path, require_c5: bool) -> tuple[list[str], bool]:
    text = card.read_text(encoding="utf-8")
    sections, fields = parse_card(text)
    errors: list[str] = []

    missing_sections = sorted(REQUIRED_SECTIONS - sections)
    if missing_sections:
        errors.append("SECTIONS_MANQUANTES=" + ",".join(missing_sections))

    by_name = {field.name: field for field in fields}
    missing_c5 = sorted(C5_FIELDS - set(by_name))
    if missing_c5:
        errors.append("CHAMPS_C5_MANQUANTS=" + ",".join(missing_c5))

    for field in fields:
        if field.status not in ALLOWED_STATUSES:
            errors.append(f"L{field.line}:STATUT_INCONNU={field.status}")
        if field.status == "mesure":
            proof_match = PROOF_RE.search(field.value)
            if not proof_match:
                errors.append(f"L{field.line}:PREUVE_REQUISE={field.name}")
                continue
            proof = resolve_proof(project_root, proof_match.group(1))
            if proof is None or not proof.is_file():
                errors.append(f"L{field.line}:PREUVE_ABSENTE_OU_HORS_PROJET={proof_match.group(1)}")
            if field.name == "mlflow run_id":
                run_match = RUN_ID_RE.search(field.value)
                if not run_match:
                    errors.append(f"L{field.line}:RUN_ID_INVALIDE")
                elif proof and proof.is_file():
                    evidence = proof.read_text(encoding="utf-8", errors="replace")
                    if run_match.group(0) not in evidence:
                        errors.append(f"L{field.line}:RUN_ID_ABSENT_DE_LA_PREUVE")

    conformite = by_name.get("classification reglementaire")
    required_phrase = "a confirmer avec le referent conformite"
    if conformite is None:
        errors.append("CLASSIFICATION_REGLEMENTAIRE_MANQUANTE")
    elif conformite.status != "a confirmer" or required_phrase not in normalized(conformite.value):
        errors.append("CLASSIFICATION_AI_ACT_NON_PRUDENTE")

    current = ""
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("## "):
            current = normalized(re.sub(r"^\d+\.\s*", "", line[3:]))
        if (
            any(marker in line for marker in MARINE_MARKERS)
            and current != "benchmark externe distinct"
        ):
            errors.append(f"L{line_number}:BENCHMARK_MARINE_HORS_SECTION_4")

    c5_ready = (
        all(name in by_name and by_name[name].status == "mesure" for name in C5_FIELDS)
        and not errors
    )
    return errors, c5_ready


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Valide structure et provenance d'une Model Card M25."
    )
    parser.add_argument("card", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--require-c5", action="store_true")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    card = args.card if args.card.is_absolute() else (project_root / args.card)
    if not card.is_file():
        print(f"MODEL_CARD_ABSENTE={card}", file=sys.stderr)
        return 2

    errors, c5_ready = validate(card.resolve(), project_root, args.require_c5)
    if errors:
        for error in errors:
            print(f"ERROR={error}", file=sys.stderr)
        print("STRUCTURE=FAIL")
        print("C4_EVIDENCE=NOT_READY")
        print("C5_EVIDENCE=NOT_READY")
        return 2

    if args.require_c5 and not c5_ready:
        print("ERROR=C5_PREUVES_REELLES_INCOMPLETES", file=sys.stderr)
        print("STRUCTURE=PASS")
        print("C4_EVIDENCE=READY_FOR_REVIEW")
        print("C5_EVIDENCE=NOT_READY")
        return 2

    print("STRUCTURE=PASS")
    print("C4_EVIDENCE=READY_FOR_REVIEW")
    print(f"C5_EVIDENCE={'READY_FOR_REVIEW' if c5_ready else 'NOT_READY'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
