"""Squelette du smoke test M28, a completer pendant la demi-journee."""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="A completer en M28 apres docker compose up")
def test_api_health_and_auth_contract() -> None:
    """Prouver /health=200, prediction sans cle=401 et prediction valide=200."""
    raise NotImplementedError
