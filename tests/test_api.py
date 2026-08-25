# =============================================================================
# FICHIER : tests/test_api.py
# RÔLE    : Tests de l'API HTTP du module 25 (l'endpoint de prédiction tabulaire).
# -----------------------------------------------------------------------------
# CE QUE CE FICHIER VÉRIFIE (vue d'ensemble, pour un·e débutant·e) :
#   - Que le service web démarre et répond (/health -> 200 "ok").
#   - Que la SÉCURITÉ d'accès fonctionne : sans clé API, on est refusé (401).
#   - Que la VALIDATION des données fonctionne : un corps de requête mal formé
#     (trop peu de relevés, ou un machine_id invalide) est rejeté proprement
#     avec un code 422 (et JAMAIS un 500 = plantage serveur).
#   - Que, dans le cas nominal, l'API renvoie bien une décision (alerte / ok)
#     accompagnée d'une probabilité de panne comprise entre 0 et 1.
#   - Que la NORMALISATION des identifiants machine marche : "M-7" est compris
#     en interne comme "MACH-07", mais la valeur BRUTE envoyée par le client
#     est conservée telle quelle dans la réponse.
#
# OUTILS CLÉS UTILISÉS ICI (à bien comprendre) :
#   * TestClient (FastAPI/Starlette) : un "faux navigateur" qui envoie des
#     requêtes HTTP à notre application SANS lancer un vrai serveur réseau.
#     Pratique et rapide pour les tests automatisés.
#   * app.dependency_overrides : un mécanisme de FastAPI qui permet de
#     REMPLACER une dépendance (ici : le modèle de Machine Learning) par une
#     fausse version pendant un test. On évite ainsi de charger un vrai modèle
#     entraîné depuis le disque : on injecte un petit modèle "jouet" à la place.
# =============================================================================

# --- Imports : on ne change RIEN ici (mêmes noms, même ordre). ---------------

# pandas : bibliothèque de manipulation de tableaux de données (DataFrame).
# On l'utilise pour fabriquer un petit jeu de données d'entraînement de test.
import pandas as pd

# TestClient : le client de test HTTP fourni par FastAPI.
# Il sait "appeler" notre application comme le ferait un vrai client web,
# mais en restant en mémoire (aucun port réseau ouvert).
from fastapi.testclient import TestClient

# app : l'objet "application FastAPI" de notre projet (l'API du module 25).
# C'est lui qui déclare les routes /health, /predict-tabular, etc.
from indusense.api.main import app

# ModelBundle      : objet "paquet" qui regroupe tout ce qu'il faut pour prédire
#                    (le modèle, sa version, le seuil de décision, la colonne cible).
# get_model_bundle : la "dépendance" FastAPI qui, normalement, fournit le vrai
#                    modèle à l'endpoint. C'est ELLE qu'on remplacera dans les tests.
from indusense.api.model_store import ModelBundle, get_model_bundle

# add_temporal_features : ajoute des colonnes "temporelles" (moyennes glissantes,
#                         tendances, etc.) au DataFrame, à partir de l'horodatage.
from indusense.features.temporal import add_temporal_features

# select_features : sélectionne les colonnes (features) utilisées pour entraîner.
# train_model     : entraîne réellement un petit modèle de classification.
from indusense.models.tabular import select_features, train_model

# TestClient(app) : on crée UNE fois le client de test, partagé par tous les tests.
# À partir de "client", on pourra faire client.get(...) et client.post(...).
client = TestClient(app)


def _bundle():
    """Fabrique un FAUX modèle (un "ModelBundle" jouet) pour les tests.

    Pourquoi ? Charger le vrai modèle entraîné (gros fichier sur le disque)
    serait lent et fragile. Ici, on entraîne en quelques millisecondes un
    mini-modèle sur des données inventées. On l'injectera ensuite à la place
    de la vraie dépendance via ``app.dependency_overrides``.

    Le ``_`` au début du nom signale, par convention Python, une fonction
    "privée"/utilitaire interne au fichier de test (pas un test en soi).
    """
    # rng : une plage de 60 dates/heures consécutives à partir du 1er janvier 2025.
    # freq="h" = un point toutes les heures ; periods=60 = 60 points au total.
    rng = pd.date_range("2025-01-01", periods=60, freq="h")

    # On construit un DataFrame (tableau) de 60 lignes avec des colonnes factices :
    df = pd.DataFrame(
        {
            "machine": "MACH-01",  # même machine pour toutes les lignes
            "timestamp": rng,  # l'horodatage défini juste au-dessus
            "temperature": range(60),  # température : 0, 1, 2, ... 59
            "pressure_bar": range(180, 240),  # pression : 180, 181, ... 239
        }
    )

    # On crée la "vérité terrain" (la cible à prédire), appelée ici "panne" :
    # règle inventée -> il y a panne (1) quand la température dépasse 40, sinon 0.
    # .astype(int) convertit les booléens True/False en entiers 1/0.
    df["panne"] = (df["temperature"] > 40).astype(int)

    # On enrichit le tableau avec les colonnes temporelles, puis on supprime
    # les lignes contenant des valeurs manquantes (NaN) générées en début de
    # série par les calculs glissants (.dropna()).
    feats = add_temporal_features(df).dropna()

    # X = les colonnes d'entrée (features) ; y = la colonne à prédire ("panne").
    X, y = select_features(feats, "panne"), feats["panne"]

    # On renvoie le "bundle" complet attendu par l'API :
    #   - model       : le modèle entraîné (10 arbres seulement -> très rapide).
    #   - version     : étiquette de version, ici "test".
    #   - threshold   : seuil de décision (proba >= 0.5 -> "alerte").
    #   - target_col  : nom de la colonne cible ("panne").
    return ModelBundle(
        model=train_model(X, y, n_estimators=10), version="test", threshold=0.5, target_col="panne"
    )


def test_health_ok():
    """Vérifie l'endpoint de "santé" du service.

    POURQUOI : /health est une route minimale qui sert à savoir si l'application
    est démarrée et répond. Les outils de supervision (monitoring) l'appellent
    régulièrement. Comportement attendu de l'API : répondre 200 avec le JSON
    {"status": "ok"}.
    """
    # client.get("/health") simule un appel HTTP GET sur /health.
    # .json() lit le corps de la réponse et le transforme en dictionnaire Python.
    # On vérifie que ce dictionnaire vaut EXACTEMENT {"status": "ok"}.
    assert client.get("/health").json() == {"status": "ok"}


def test_missing_api_key_returns_401():
    """Vérifie que SANS clé API, l'accès à l'endpoint protégé est REFUSÉ.

    POURQUOI : /predict-tabular est une route protégée. Le client doit fournir
    l'en-tête "X-API-Key". S'il l'oublie, l'API doit répondre 401 (Unauthorized)
    = "non authentifié". On ne traite surtout pas la requête.
    """
    # On envoie une requête POST SANS l'en-tête X-API-Key (volontairement).
    # Le corps JSON est valide en apparence, mais peu importe : l'absence de clé
    # doit faire échouer la requête AVANT tout traitement métier.
    r = client.post("/predict-tabular", json={"machine_id": "MACH-01", "readings": []})

    # Comportement attendu : code HTTP 401 (accès non autorisé, clé manquante).
    assert r.status_code == 401


def test_insufficient_readings_returns_422():
    """Vérifie le rejet d'une requête contenant TROP PEU de relevés.

    POURQUOI : pour calculer les features temporelles (moyennes glissantes...),
    il faut un minimum de relevés (au moins 7). Ici, on en envoie 0 (liste vide).
    L'API doit refuser avec un code 422 (Unprocessable Entity) = "la donnée
    est syntaxiquement reçue mais ne respecte pas les règles de validation".
    """
    r = client.post(
        "/predict-tabular",
        # Cette fois, on FOURNIT bien la clé API : on dépasse l'étape 401.
        headers={"X-API-Key": "dev-key"},
        # "readings": [] -> liste vide = 0 relevé, soit moins que le minimum requis.
        json={"machine_id": "MACH-01", "readings": []},
    )

    # Comportement attendu : 422, car le contenu est invalide (pas assez de relevés).
    assert r.status_code == 422


def test_predict_ok_with_bundle():
    """Vérifie le SCÉNARIO NOMINAL : une requête correcte renvoie une décision.

    POINT CLÉ PÉDAGOGIQUE : on injecte ici un faux modèle via
    ``app.dependency_overrides`` pour que l'endpoint ait quelque chose avec
    quoi prédire, sans dépendre d'un vrai modèle entraîné sur disque.
    """
    # app.dependency_overrides[get_model_bundle] = _bundle :
    #   -> on dit à FastAPI : "quand l'endpoint réclame le modèle (get_model_bundle),
    #      appelle MA fonction _bundle à la place". C'est l'INJECTION du faux modèle.
    app.dependency_overrides[get_model_bundle] = _bundle

    # On fabrique 8 relevés horaires valides (8 >= 7, donc assez pour prédire).
    # Chaque relevé a un timestamp, une température et une pression croissantes.
    readings = [
        {
            "timestamp": f"2025-02-01T{h:02d}:00:00",  # ex : 2025-02-01T00:00:00, ...07:00:00
            "temperature": 50 + h,  # 50, 51, ... 57
            "pressure_bar": 195 + h * 0.5,  # 195.0, 195.5, ... 198.5
        }
        for h in range(8)  # h va de 0 à 7 -> 8 relevés
    ]

    # On envoie la requête POST complète : clé API + machine_id + 8 relevés.
    # Remarque : on utilise "MACH-07", un identifiant déjà au format canonique.
    r = client.post(
        "/predict-tabular",
        headers={"X-API-Key": "dev-key"},
        json={"machine_id": "MACH-07", "readings": readings},
    )

    # On RETIRE le faux modèle pour ne pas "polluer" les tests suivants.
    # .clear() remet la table des overrides à vide : l'API retrouve son état normal.
    app.dependency_overrides.clear()

    # Comportement attendu : tout est valide -> code 200 (succès).
    assert r.status_code == 200

    # b : le corps de la réponse, converti en dictionnaire Python.
    b = r.json()

    # Deux vérifications combinées (and) sur la réponse :
    #   1) proba_panne est bien une probabilité, donc entre 0.0 et 1.0 inclus.
    #   2) decision est l'une des deux valeurs attendues : "alerte" ou "ok".
    assert 0.0 <= b["proba_panne"] <= 1.0 and b["decision"] in {"alerte", "ok"}


def _readings():
    """Fabrique 8 relevés valides, réutilisables par plusieurs tests.

    On extrait cette liste dans une petite fonction utilitaire pour éviter de
    recopier le même code (principe DRY : "Don't Repeat Yourself"). Le contenu
    est identique aux relevés du test nominal ci-dessus.
    """
    return [
        {
            "timestamp": f"2025-02-01T{h:02d}:00:00",
            "temperature": 50 + h,
            "pressure_bar": 195 + h * 0.5,
        }
        for h in range(8)
    ]


def test_predict_normalizes_noncanonical_machine_id():
    """Bord API : un client envoyant ``M-7`` est canonicalisé en interne (MACH-07) -> 200.

    Le ``machine_id`` brut est conservé en sortie
    (convention 95 §2 : brut entrant, canonique interne).
    """
    # ----- Explications détaillées pour débutant·e (au-dessus du docstring d'origine) :
    # Idée du test : le client est "tolérant à la saisie". Il peut écrire un
    # identifiant non canonique comme "M-7". En INTERNE, l'API le NORMALISE en
    # "MACH-07" (format officiel) pour retrouver la bonne machine. Mais en SORTIE,
    # l'API renvoie la valeur BRUTE telle que le client l'a envoyée ("M-7"),
    # sans la réécrire. Conséquences attendues :
    #   - la requête réussit -> 200 (la normalisation interne a permis de prédire),
    #   - le champ machine_id de la réponse vaut toujours "M-7" (brut conservé).

    # On réinjecte le faux modèle (même mécanisme que le test nominal).
    app.dependency_overrides[get_model_bundle] = _bundle

    # Requête valide, mais avec un machine_id NON canonique : "M-7".
    r = client.post(
        "/predict-tabular",
        headers={"X-API-Key": "dev-key"},
        json={"machine_id": "M-7", "readings": _readings()},
    )

    # On nettoie l'override juste après l'appel.
    app.dependency_overrides.clear()

    # Comportement attendu n°1 : la normalisation interne réussit -> 200.
    assert r.status_code == 200

    # Comportement attendu n°2 : la sortie conserve la valeur BRUTE "M-7"
    # (et NE la remplace PAS par la forme canonique "MACH-07").
    assert r.json()["machine_id"] == "M-7"  # brut conservé, pas réécrit en MACH-07


def test_predict_invalid_machine_id_returns_422():
    """Bord API : un ``machine_id`` sans numéro (``NOPE``) lève ValueError -> 422 (jamais 500)."""
    # ----- Explications détaillées pour débutant·e :
    # Ici, l'identifiant "NOPE" ne contient AUCUN numéro de machine exploitable.
    # La normalisation interne ne peut donc pas le transformer en "MACH-xx" :
    # le code lève une ValueError. Le point important : l'API doit ATTRAPER cette
    # erreur et la transformer en réponse 422 (donnée invalide côté client),
    # et surtout PAS la laisser remonter en 500 (erreur serveur = bug non géré).
    # Règle d'or : une mauvaise saisie du client -> 4xx ; un bug interne -> 5xx.

    # On injecte le faux modèle (l'erreur doit survenir AVANT/PENDANT la validation
    # du machine_id, pas à cause d'un modèle manquant).
    app.dependency_overrides[get_model_bundle] = _bundle

    # Requête par ailleurs correcte (clé API + 8 relevés valides), mais machine_id "NOPE".
    r = client.post(
        "/predict-tabular",
        headers={"X-API-Key": "dev-key"},
        json={"machine_id": "NOPE", "readings": _readings()},
    )

    # On nettoie l'override.
    app.dependency_overrides.clear()

    # Comportement attendu : 422 (machine_id invalide), et JAMAIS 500.
    assert r.status_code == 422
