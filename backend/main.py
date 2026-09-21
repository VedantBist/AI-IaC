from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import joblib
import numpy as np
from fastapi import HTTPException
from pathlib import Path

from ml.model_registry import MODEL_REGISTRY, public_model_metadata


app = FastAPI(
    title="AI Prediction Service",
    description="Multi-model scikit-learn prediction API",
    version="1.0"
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# MODEL
# --------------------------------------------------

MODELS = {}
for model_id, metadata in MODEL_REGISTRY.items():
    artifact = Path(metadata["artifact"])
    if artifact.exists():
        MODELS[model_id] = joblib.load(artifact)


# --------------------------------------------------
# REQUEST MODEL
# --------------------------------------------------

class PredictionRequest(BaseModel):
    model: str = "breast_cancer"
    features: list[float] = Field(..., min_length=1)


@app.get("/models")
def models():
    return {"models": public_model_metadata()}


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.get("/")
def home():

    return {
        "message": "AI Prediction Service is running",
        "status": "active"
    }


# --------------------------------------------------
# PREDICTION
# --------------------------------------------------

@app.post("/predict")
def predict(request: PredictionRequest):

    metadata = MODEL_REGISTRY.get(request.model)
    model = MODELS.get(request.model)

    if metadata is None or model is None:
        raise HTTPException(status_code=404, detail="Unknown or unavailable model.")

    if len(request.features) != metadata["features"]:
        raise HTTPException(
            status_code=422,
            detail=f"Model '{request.model}' expects exactly {metadata['features']} features.",
        )

    input_data = np.array(
        request.features
    ).reshape(1, -1)

    prediction = model.predict(input_data)[0]
    response = {"model": request.model, "class": int(prediction) if metadata["task"] != "Regression" else None}

    if metadata["task"] == "Regression":
        response["prediction"] = round(float(prediction), 4)
    else:
        response["prediction"] = metadata["labels"][int(prediction)]

    return response