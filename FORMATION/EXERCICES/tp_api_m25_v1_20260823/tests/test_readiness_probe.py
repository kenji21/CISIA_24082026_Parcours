from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from indusense.api.main import app
from indusense.api.model_store import get_model_bundle
from indusense.config import settings

client = TestClient(app)


@contextmanager
def model_unavailable() -> Iterator[None]:
    """Remplace seulement get_model_bundle, puis restaure son état exact."""
    overrides = app.dependency_overrides
    marker = object()
    previous = overrides.get(get_model_bundle, marker)
    overrides[get_model_bundle] = lambda: None
    try:
        yield
    finally:
        if previous is marker:
            overrides.pop(get_model_bundle, None)
        else:
            overrides[get_model_bundle] = previous


def readings() -> list[dict[str, object]]:
    return [
        {
            "timestamp": f"2025-02-01T{hour:02d}:00:00",
            "temperature": 50 + hour,
            "pressure_bar": 195 + hour * 0.5,
        }
        for hour in range(8)
    ]


def test_ready_returns_exact_503_when_model_is_unavailable() -> None:
    with model_unavailable():
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Modele non charge"}


def test_predict_tabular_returns_exact_503_after_auth_and_validation() -> None:
    with model_unavailable():
        response = client.post(
            "/predict-tabular",
            headers={"X-API-Key": settings.api_key},
            json={"machine_id": "MACH-01", "readings": readings()},
        )

    assert response.status_code == 503
    assert response.json() == {"detail": "Modele non charge"}
