from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import numpy as np
import os


app = FastAPI(
    title="AI Prediction Service",
    description="Breast Cancer Prediction API",
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

MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "ml",
    "model.pkl"
)

model = joblib.load(MODEL_PATH)


# --------------------------------------------------
# REQUEST MODEL
# --------------------------------------------------

class PredictionRequest(BaseModel):
    features: list[float]


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

    input_data = np.array(
        request.features
    ).reshape(1, -1)

    prediction = model.predict(input_data)[0]

    if prediction == 0:
        result = "Malignant"
    else:
        result = "Benign"

    return {
        "prediction": result,
        "class": int(prediction)
    }