"""Controle pedagogique de taille et d'utilisateur d'une image M27."""

from __future__ import annotations

import subprocess
import sys

IMAGE = sys.argv[1] if len(sys.argv) > 1 else "indusense:0.1.0"
MAX_MB = 200


def docker(*args: str) -> str:
    result = subprocess.run(
        ["docker", *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


size_mb = int(docker("image", "inspect", IMAGE, "--format", "{{.Size}}")) / (1024 * 1024)
user = docker("run", "--rm", "--entrypoint", "whoami", IMAGE)

problems = []
if size_mb > MAX_MB:
    problems.append(f"taille {size_mb:.0f} Mo > {MAX_MB} Mo")
if user == "root":
    problems.append("conteneur en root (attendu : appuser)")
if problems:
    raise SystemExit("ECHEC : " + " ; ".join(problems))

print(f"OK : {size_mb:.0f} Mo, user={user}")
