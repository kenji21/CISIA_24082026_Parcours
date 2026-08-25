# Surcouche de preuves M25 — API et Model Card

Version : **v2 multiplateforme — 23/08/2026**. Cette ressource complète le dépôt
CISIA ouvert par l'apprenant sans le remplacer. Elle ajoute deux tests 503 et une porte de
Model Card fondée sur la structure, le statut des informations et leurs preuves.

## Ce que la surcouche prouve

- `/ready` refuse le trafic avec **503** quand le modèle n'est pas chargé ;
- `/predict-tabular` refuse aussi avec **503** après authentification et validation ;
- l'override FastAPI est restauré exactement après chaque test ;
- la Model Card comporte les trois niveaux attendus ;
- une valeur marquée `[mesuré]` pointe vers un fichier local existant ;
- un `run_id` marqué `[mesuré]` est plausible et apparaît dans sa preuve ;
- les chiffres Marine restent dans une section de benchmark externe distincte ;
- la classification AI Act reste `[à confirmer]` avec le référent conformité ;
- la porte C5 reste `NOT_READY` tant que run, données, métriques et seuil ne sont
  pas réellement prouvés. Un passage vert signifie **prêt pour revue**, jamais
  « compétence acquise » automatiquement.

## Installation recommandée — Windows, macOS et Linux

Dans VS Code, ouvrir la racine du projet puis **Terminal > Nouveau terminal**.
La première commande prépare l'environnement exclusivement à partir du verrou ;
la deuxième applique la surcouche avec le même Python 3.13 sur les trois
systèmes. Un fichier déjà identique n'est pas recopié ; un homonyme différent
est sauvegardé dans le dossier temporaire du système. Aucun `.bak` n'est créé
dans le dépôt et `uv.lock` est contrôlé avant/après.

```text
uv sync --frozen --extra dev
uv run --frozen python FORMATION/EXERCICES/tp_api_m25_v1_20260823/APPLIQUER_PREUVES_M25.py .
uv run pytest -q tests/test_api.py tests/test_readiness_probe.py tests/test_model_card_gate.py
uv run python scripts/validate_model_card.py docs/model_card.md --project-root .
git status --short -- uv.lock
```

Si la ressource a été remise à côté d'un autre clone, adaptez uniquement son
chemin :

```text
uv sync --frozen --extra dev
uv run --frozen python ../tp_api_m25_v1_20260823/APPLIQUER_PREUVES_M25.py .
uv run pytest -q tests/test_api.py tests/test_readiness_probe.py tests/test_model_card_gate.py
uv run python scripts/validate_model_card.py docs/model_card.md --project-root .
git status --short -- uv.lock
```

La dernière commande ne doit rien afficher. Si elle affiche `uv.lock`, arrêter
et prévenir le formateur.

### Alternative Windows PowerShell

Le script PowerShell historique reste disponible pour les postes Windows. Il
offre les mêmes sauvegardes et contrôles, mais la voie Python ci-dessus est la
référence commune à la classe :

```powershell
$overlay = (Resolve-Path -LiteralPath '..\tp_api_m25_v1_20260823').Path
& (Join-Path $overlay 'APPLIQUER_PREUVES_M25.ps1') -ProjectPath .
if (-not $?) { throw 'Application de la surcouche M25 impossible.' }
```

Résultat attendu avec le dépôt canonique et le modèle de carte livré :

```text
12 passed
STRUCTURE=PASS
C4_EVIDENCE=READY_FOR_REVIEW
C5_EVIDENCE=NOT_READY
```

Le nombre `12` correspond aux **6 tests API canoniques + 2 tests 503 + 4 tests
de la porte Model Card**. Si le dépôt évolue, retenir surtout **0 échec** et les
noms des tests collectés, pas un compteur mémorisé.

## Porte C5 stricte, seulement quand les preuves existent

Après avoir remplacé les statuts `[à produire]` par `[mesuré]` et ajouté les
chemins `preuve=...` vers de vrais artefacts locaux :

```text
uv run --frozen python scripts/validate_model_card.py docs/model_card.md --project-root . --require-c5
```

Un code de sortie non nul signifie : conserver `NOT_READY` et compléter les
preuves réelles. Ne contournez pas cette porte.

Résultat attendu uniquement si les quatre familles de preuves sont retrouvables :

```text
STRUCTURE=PASS
C4_EVIDENCE=READY_FOR_REVIEW
C5_EVIDENCE=READY_FOR_REVIEW
```

## Plans B

- **Hors ligne** : si le cache `uv` du poste est déjà préparé, utiliser
  `uv sync --frozen --extra dev --offline`. Sinon, le formateur fournit une
  copie du projet avec `.venv` synchronisé ; ne pas installer au hasard.
- **Sans modèle, GPU ou Docker** : les tests utilisent `TestClient` et un
  override de dépendance ; aucun serveur, GPU, modèle binaire ni conteneur n'est
  requis.
- **MLflow indisponible** : garder `MLflow run_id : [à produire]`. La structure
  peut passer ; la porte C5 doit rester `NOT_READY`.

## Diagnostic rapide

| Symptôme | Cause probable | Correction |
|---|---|---|
| 401 au lieu de 503 sur `/predict-tabular` | clé absente/invalide | le test fournit `settings.api_key` |
| 422 au lieu de 503 | moins de 7 relevés ou corps invalide | conserver les 8 relevés du test |
| carte verte avec seulement des titres | mauvais validateur appelé | exécuter `scripts/validate_model_card.py` de cette surcouche |
| `PREUVE_ABSENTE` | chemin `preuve=...` faux ou hors projet | utiliser un chemin relatif vers un fichier existant |
| `BENCHMARK_MARINE_HORS_SECTION_4` | chiffre Marine attribué au modèle | déplacer le repère dans `## 4. Benchmark externe distinct` |
| `C5_EVIDENCE=NOT_READY` | preuve réelle incomplète | produire run, données/split/hash, métriques et seuil ; ne rien inventer |
