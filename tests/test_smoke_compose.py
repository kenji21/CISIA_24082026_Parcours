"""Smoke test M28 : prouver que la stack Compose répond VRAIMENT, de l'extérieur.

DIFFÉRENCE CAPITALE AVEC test_api.py
------------------------------------
`test_api.py` utilise `TestClient(app)` : il appelle l'application Python EN
MÉMOIRE, dans le processus pytest. Aucun réseau, aucun conteneur — c'est rapide
et parfait pour tester la logique, mais ça ne prouve RIEN sur Docker.

Ici, on fait l'inverse : on parle à l'API par le RÉSEAU, sur
http://localhost:8000, c'est-à-dire au conteneur `api` lancé par
`docker compose up -d`. Ce test valide donc toute la chaîne du module 28 :
image construite -> conteneur démarré -> port publié (8000:8000) -> `.env` bien
injecté -> modèle chargé. Si un seul de ces maillons casse, ce test échoue.

MODE D'EMPLOI (cf. FORMATION/JALONS/06-j3-apres-midi-m28.md) :

    docker compose up -d --build
    uv run pytest tests/test_smoke_compose.py -q
    docker compose down

Si la stack n'est pas lancée, le test se met en SKIP avec un message explicite
(et non une pile d'erreurs réseau illisible).
"""

from __future__ import annotations

import os
from collections.abc import Iterator

# httpx : client HTTP moderne (c'est celui qui propulse le TestClient de FastAPI,
# il est donc déjà installé). Ici on s'en sert pour de VRAIES requêtes réseau.
import httpx
import pytest

# On réutilise la configuration du projet pour connaître la clé API attendue.
# POURQUOI c'est la bonne source : `settings` lit le fichier `.env` (préfixe
# INDUSENSE_), et le docker-compose.yml injecte CE MÊME fichier dans le
# conteneur via `INDUSENSE_API_KEY: ${INDUSENSE_API_KEY}`. Le test et l'API
# partagent donc une unique source de vérité — on n'écrit aucun secret ici.
from indusense.config import settings

# Adresse de la stack. Surchargeable pour un cas particulier (ex. Docker distant) :
#   SMOKE_BASE_URL=http://192.168.1.10:8000 uv run pytest tests/test_smoke_compose.py
# NB : volontairement SANS le préfixe INDUSENSE_, pour ne pas se mélanger avec
# les réglages applicatifs lus par `settings`.
BASE_URL = os.getenv("SMOKE_BASE_URL", "http://localhost:8000")

# Délai maximal d'attente d'une réponse. 5 s : large pour du local, mais assez
# court pour ne pas figer la séance si rien n'écoute sur le port.
TIMEOUT_SECONDES = 5.0


def _readings() -> list[dict]:
    """Fabrique 8 relevés valides, cohérents et croissants dans le temps.

    Pourquoi 8 et pas 3 ? Le schéma `TabularPredictionRequest` impose
    `min_length=7` : le modèle calcule des features temporelles (lags jusqu'à 6
    pas, moyennes glissantes), donc il lui faut assez de passé. En envoyer 8
    garantit qu'il reste au moins une ligne exploitable après `.dropna()`.
    """
    return [
        {
            "timestamp": f"2025-02-01T{h:02d}:00:00",
            "temperature": 50 + h,
            "pressure_bar": 195 + h * 0.5,
        }
        for h in range(8)
    ]


@pytest.fixture
def stack() -> Iterator[httpx.Client]:
    """Client HTTP vers la stack Compose, ou SKIP si elle n'est pas lancée.

    Le `with` garantit la fermeture propre de la connexion à la fin du test.
    La requête sur /health sert de « coup de sonde » : si personne ne répond sur
    le port, mieux vaut un skip lisible qu'une ConnectionError brute.
    """
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT_SECONDES) as client:
        try:
            client.get("/health")
        except httpx.RequestError:
            pytest.skip(
                f"Stack Compose injoignable sur {BASE_URL} : lancer "
                "`docker compose up -d --build` avant ce smoke test."
            )
        yield client


def test_api_health_and_auth_contract(stack: httpx.Client) -> None:
    """Prouver /health=200, prediction sans cle=401 et prediction valide=200."""
    # --- 1) LIVENESS : le conteneur est vivant et le port 8000 est bien publié.
    reponse = stack.get("/health")
    assert reponse.status_code == 200, (
        f"/health a répondu {reponse.status_code} : le conteneur api tourne-t-il ? "
        "Vérifier `docker compose ps` et `docker compose logs api`."
    )
    assert reponse.json() == {"status": "ok"}

    # --- 2) AUTHENTIFICATION : sans clé, la route de prédiction doit refuser.
    # Détail qui compte : on envoie ici un corps JSON PARFAITEMENT VALIDE. Ainsi,
    # si l'API répond 401, c'est forcément à cause de la clé manquante et non
    # d'un problème de données (qui donnerait un 422). Le test est sans ambiguïté.
    reponse = stack.post(
        "/predict-tabular",
        json={"machine_id": "MACH-01", "readings": _readings()},
    )
    assert reponse.status_code == 401, (
        f"Attendu 401 sans clé API, obtenu {reponse.status_code}. "
        "Une route sensible exposée sans authentification est une faille."
    )

    # --- 3) CAS NOMINAL : avec la bonne clé, la prédiction doit aboutir.
    reponse = stack.post(
        "/predict-tabular",
        headers={"X-API-Key": settings.api_key},
        json={"machine_id": "MACH-01", "readings": _readings()},
    )
    # Deux échecs fréquents, qu'on explicite pour ne pas chercher à l'aveugle :
    assert reponse.status_code != 401, (
        "401 avec la clé du .env : le conteneur n'a pas la même clé que ce test. "
        "Lancer pytest depuis le dossier contenant docker-compose.yml et .env, "
        "et recréer le conteneur après toute modification du .env "
        "(`docker compose up -d api`)."
    )
    assert reponse.status_code != 503, (
        "503 « Modèle non chargé » : l'image ne contient pas de modèle entraîné. "
        "Vérifier GET /ready et la présence de artifacts/models dans l'image."
    )
    assert reponse.status_code == 200, f"Attendu 200, obtenu {reponse.status_code}"

    # Le code 200 ne suffit pas : on vérifie aussi le CONTRAT DE SORTIE, c'est-à-dire
    # que la réponse contient bien ce que les clients attendent.
    corps = reponse.json()
    assert corps["machine_id"] == "MACH-01"  # l'ID est renvoyé tel qu'envoyé
    assert 0.0 <= corps["proba_panne"] <= 1.0  # une probabilité reste dans [0, 1]
    assert corps["decision"] in {"ok", "alerte"}  # la décision est l'une des deux valeurs
    assert corps["model_version"]  # traçabilité : on sait quel modèle a répondu
