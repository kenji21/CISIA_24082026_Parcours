# =============================================================================
# FICHIER : tests/test_security.py
# RÔLE    : Tests des PROTECTIONS de sécurité du module 26 (garde-fous de l'API).
# -----------------------------------------------------------------------------
# CE QUE CE FICHIER VÉRIFIE (vue d'ensemble, pour un·e débutant·e) :
#   - La protection "PAYLOAD TROP GROS" : si un client envoie un corps de requête
#     plus volumineux que la limite autorisée, l'API refuse avec un code 413
#     (Payload Too Large). But : éviter qu'une requête énorme ne sature la mémoire
#     ou ne serve à attaquer le service (déni de service).
#   - La protection "RATE LIMIT" (limitation de débit) : un même client ne peut
#     pas envoyer un nombre illimité de requêtes dans une fenêtre de temps donnée.
#     Une fois la limite atteinte, la requête suivante est rejetée avec un code 429
#     (Too Many Requests). But : empêcher les abus / le matraquage de l'API.
#
# CES DEUX MÉCANISMES VIVENT DANS LE MODULE ``indusense.api.security``.
# Les tests appellent soit l'API entière (via TestClient), soit DIRECTEMENT les
# fonctions/variables internes de ce module de sécurité pour les vérifier finement.
# =============================================================================

# --- Imports : on ne change RIEN ici (mêmes noms, même ordre). ---------------

# pytest : le framework de tests. On s'en sert ici notamment pour
# ``pytest.raises(...)``, qui permet de vérifier qu'un bloc de code lève bien
# une exception attendue (sinon le test échoue).
import pytest

# HTTPException : l'exception "HTTP" de FastAPI. Quand le code de sécurité veut
# renvoyer une erreur HTTP (ex : 429), il lève une HTTPException portant le code.
from fastapi import HTTPException

# TestClient : le "faux navigateur" qui appelle notre application sans ouvrir de
# vrai port réseau (voir explications détaillées dans test_api.py).
from fastapi.testclient import TestClient

# security : le module qui contient les garde-fous (limite de taille du corps,
# limitation de débit, et leurs constantes/états internes).
from indusense.api import security

# app : l'application FastAPI complète (avec ses routes et ses middlewares de sécurité).
from indusense.api.main import app

# On crée le client de test une seule fois, partagé par les tests de ce fichier.
client = TestClient(app)


def test_payload_too_large_returns_413():
    """Vérifie que l'API rejette un corps de requête TROP VOLUMINEUX (-> 413).

    POURQUOI : pour se protéger, l'API fixe une taille maximale de corps,
    stockée dans ``security.MAX_BODY_BYTES``. Si le corps dépasse cette limite,
    elle doit répondre 413 (Payload Too Large) sans même tenter de traiter
    la requête. Cela évite la surconsommation de mémoire et certaines attaques.
    """
    r = client.post(
        "/predict-tabular",
        # On fournit la clé API : on veut tester la limite de TAILLE, pas l'auth.
        headers={"X-API-Key": "dev-key"},
        # content=... : ici on envoie un corps BRUT (octets), pas du JSON.
        #   b"x" * (MAX_BODY_BYTES + 1) construit une chaîne d'octets composée
        #   de la lettre "x" répétée (limite autorisée + 1) fois.
        #   -> volontairement UN octet de trop pour DÉPASSER la limite.
        content=b"x" * (security.MAX_BODY_BYTES + 1),
    )

    # Comportement attendu : 413, car le corps dépasse la taille maximale permise.
    assert r.status_code == 413


def test_invalid_content_length_returns_400():
    """Une taille déclarée illisible doit produire une erreur client, jamais un crash serveur."""
    r = client.post(
        "/predict-tabular",
        headers={"X-API-Key": "dev-key", "Content-Length": "pas-un-entier"},
        content=b"{}",
    )

    assert r.status_code == 400
    assert r.json() == {"detail": "Content-Length invalide"}


def test_rate_limit_policy_is_not_exposed_as_query_parameters():
    """Un client ne doit pas pouvoir augmenter la limite via ``?limit=`` ou ``?window=``."""
    operation = app.openapi()["paths"]["/predict-tabular"]["post"]
    parameter_names = {parameter["name"] for parameter in operation.get("parameters", [])}

    assert "limit" not in parameter_names
    assert "window" not in parameter_names


def test_rate_limit_blocks_after_limit():
    """Vérifie la LIMITATION DE DÉBIT : au-delà de N requêtes, on bloque (-> 429).

    POURQUOI : un même client (identifié par son adresse IP) ne doit pas pouvoir
    inonder l'API. La fonction ``security.rate_limit`` compte les appels d'une IP
    dans une fenêtre de temps. Tant qu'on est sous la limite, elle laisse passer ;
    dès qu'on la dépasse, elle lève une HTTPException avec le code 429.

    NOTE : ce test appelle DIRECTEMENT la fonction interne ``rate_limit`` (au lieu
    de passer par TestClient). On peut ainsi simuler précisément le compteur et
    fabriquer de faux objets "requête" minimalistes.
    """
    # security._hits : le "compteur" interne (mémoire des appels par IP).
    # On le VIDE au début pour partir d'un état propre, indépendant des autres tests.
    # Le ``_`` devant ``_hits`` signale une variable interne/privée du module.
    security._hits.clear()

    # On fabrique de FAUX objets très simples pour imiter ce que ``rate_limit``
    # attend en entrée. Pas besoin d'une vraie requête HTTP complète :
    # il suffit de fournir la même "forme" (les attributs réellement lus).

    class _Client:
        # rate_limit lit l'adresse IP via req.client.host : on en met une factice.
        host = "9.9.9.9"

    class _Req:
        # rate_limit lit req.client : on lui donne une instance de _Client ci-dessus.
        client = _Client()

    # req : notre fausse requête, vue par rate_limit comme venant de l'IP 9.9.9.9.
    req = _Req()

    # On appelle rate_limit EXACTEMENT 60 fois (limit=60), dans une fenêtre de 60s.
    # Ces 60 appels sont PILE à la limite : ils doivent TOUS passer sans erreur.
    for _ in range(60):
        security.rate_limit(req, limit=60, window=60.0)

    # Le 61e appel dépasse la limite : on s'attend à ce qu'il LÈVE une HTTPException.
    # ``with pytest.raises(HTTPException) as e:`` -> le test réussit seulement si
    # une HTTPException est bien levée à l'intérieur du bloc (sinon il échoue).
    with pytest.raises(HTTPException) as e:
        # Cet appel supplémentaire (le 61e) doit être REFUSÉ.
        security.rate_limit(req, limit=60, window=60.0)

    # e.value : l'exception réellement levée. On vérifie que son code HTTP est 429
    # (Too Many Requests), confirmant que la limitation de débit a bien bloqué.
    assert e.value.status_code == 429
