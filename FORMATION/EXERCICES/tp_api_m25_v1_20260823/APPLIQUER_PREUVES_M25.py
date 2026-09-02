"""Applique la surcouche M25 de façon idempotente sur Windows, macOS et Linux."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

COPIES = (
    Path("tests/test_readiness_probe.py"),
    Path("tests/test_model_card_gate.py"),
    Path("tests/fixtures/model_card_template.md"),
    Path("scripts/validate_model_card.py"),
)
REQUIRED = (Path("templates/model_card.md"), Path("README.md"), *COPIES)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Appliquer la surcouche de preuves M25 sans modifier uv.lock."
    )
    parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="racine du projet cible (défaut : dossier courant)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    overlay = Path(__file__).resolve().parent
    project = Path(args.project_path).expanduser().resolve(strict=True)
    lock_path = project / "uv.lock"
    if not lock_path.is_file():
        raise SystemExit("Le dossier cible n'est pas la racine du projet CISIA : uv.lock absent.")

    for relative in REQUIRED:
        if not (overlay / relative).is_file():
            raise SystemExit(f"Surcouche M25 incomplète : {relative.as_posix()} est absent.")

    lock_before = sha256(lock_path)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_root = Path(tempfile.gettempdir()) / f"CISIA_M25_backup_{stamp}"
    backup_used = False

    for relative in COPIES:
        source = overlay / relative
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            if sha256(source) == sha256(target):
                print(f"DEJA_IDENTIQUE {relative.as_posix()}")
                continue
            backup_target = backup_root / relative
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup_target)
            backup_used = True
            print(f"SAUVEGARDE {relative.as_posix()} -> {backup_target}")

        shutil.copy2(source, target)
        print(f"INSTALLE {relative.as_posix()}")

    card = project / "docs/model_card.md"
    if card.exists():
        print("PRESERVE docs/model_card.md")
    else:
        card.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay / "templates/model_card.md", card)
        print("INITIALISE docs/model_card.md")

    if sha256(lock_path) != lock_before:
        raise SystemExit("uv.lock a changé pendant l'application de la surcouche M25.")

    print(f"BACKUP_ROOT={backup_root if backup_used else 'NON_NECESSAIRE'}")
    print("M25_OVERLAY=READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
