# Jalon actuel : 04-j2-apres-midi-m26

Etat revele pour J2 apres-midi : API M25 et activite securite M26.

- Source locale de provenance : starter remis au precedent groupe au demarrage
  du Sprint 3, commit historique `0d02af0`.
- Ce n'est pas un snapshot « fin S2 pur » : le package, les tests, la CI et
  pre-commit amorcent volontairement M23/M24 pour garantir un depart commun.
- La reference data-science semantique de fin S2 (Marine) reste separee ; ses
  chiffres et artefacts ne sont pas fusionnes avec le RF starter.
- Donnees, modele RF, metadata, package minimal et tests sont presents.
- Aucun Dockerfile, Compose, orchestration Prefect, drift ou Game Day n'est
  revele dans ce jalon.

Ce jalon n'est pas nomme `baseline_stagiaire_exacte`, car le dernier checkout
reel de ce groupe en fin M22 n'est pas present dans les sources locales.

Details et empreintes : [`PROVENANCE_SOCLE.md`](PROVENANCE_SOCLE.md).

Preuve attendue :

```powershell
uv sync --frozen --extra dev
uv run pytest -q
uv run ruff check .
uv run indusense --help
```
