"""API M25 : contrat, readiness, authentification et prediction tabulaire.

Les protections de taille de corps et de debit arrivent au jalon M26.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status

import indusense.api.model_store as store
from indusense.api.model_store import ModelBundle, get_model_bundle
from indusense.api.schemas import PredictionResponse, TabularPredictionRequest
from indusense.config import settings
from indusense.data.loaders import normalize_machine_id
from indusense.features.temporal import add_temporal_features
from indusense.models.tabular import predict_proba, select_features


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        store._BUNDLE = store.load_bundle(settings.model_dir, settings.decision_threshold)
    except FileNotFoundError:
        store._BUNDLE = None
    yield


app = FastAPI(title="InduSense API", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def require_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> None:
    if x_api_key is None or x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cle API absente ou invalide",
        )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
def ready(bundle: ModelBundle | None = Depends(get_model_bundle)) -> dict:
    if bundle is None:
        raise HTTPException(status_code=503, detail="Modele non charge")
    return {"status": "ready", "model_version": bundle.version}


@app.post(
    "/predict-tabular",
    response_model=PredictionResponse,
    dependencies=[Depends(require_api_key)],
)
def predict_tabular(
    payload: TabularPredictionRequest,
    bundle: ModelBundle | None = Depends(get_model_bundle),
) -> PredictionResponse:
    if bundle is None:
        raise HTTPException(status_code=503, detail="Modele non charge")

    frame = pd.DataFrame([reading.model_dump() for reading in payload.readings])
    try:
        frame["machine"] = normalize_machine_id(payload.machine_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    features = add_temporal_features(frame).dropna()
    if features.empty:
        raise HTTPException(status_code=422, detail="Historique insuffisant")

    model_input = select_features(features, bundle.target_col).iloc[[-1]]
    probability = float(predict_proba(bundle.model, model_input)[0])
    return PredictionResponse(
        machine_id=payload.machine_id,
        proba_panne=probability,
        decision="alerte" if probability >= bundle.threshold else "ok",
        model_version=bundle.version,
        threshold=bundle.threshold,
    )
