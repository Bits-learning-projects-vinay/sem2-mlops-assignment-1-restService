import os
import pickle

import boto3
import pandas as pd
from botocore.exceptions import BotoCoreError, ClientError
from flask import Flask, jsonify, request

_CACHED_MODEL = None


def load_model_from_s3(bucket_name, object_key, region_name=None, s3_client=None):
    """Download a pickled model from S3 and deserialize it."""
    client = s3_client or boto3.client("s3", region_name=region_name)
    response = client.get_object(Bucket=bucket_name, Key=object_key)
    model_bytes = response["Body"].read()
    return pickle.loads(model_bytes)


def get_model(s3_client=None):
    """Cache model in memory to avoid repeated S3 downloads."""
    global _CACHED_MODEL
    if _CACHED_MODEL is not None:
        return _CACHED_MODEL

    bucket = os.environ.get("MODEL_S3_BUCKET")
    key = os.environ.get("MODEL_S3_KEY")
    region = os.environ.get("MODEL_S3_REGION")

    if not bucket or not key:
        raise ValueError(
            "Environment variables MODEL_S3_BUCKET and MODEL_S3_KEY are required."
        )

    _CACHED_MODEL = load_model_from_s3(
        bucket_name=bucket,
        object_key=key,
        region_name=region,
        s3_client=s3_client,
    )
    return _CACHED_MODEL


def normalize_features(features):
    """Accept list-of-dicts (DataFrame style) or list-of-lists input."""
    if isinstance(features, list) and features and isinstance(features[0], dict):
        return pd.DataFrame(features)
    return features


def _to_json_safe(value):
    """Convert numpy/pandas types to JSON-serializable lists."""
    if hasattr(value, "tolist"):
        return value.tolist()
    return value


def _extract_probability(proba):
    """Helper to extract positive class probability from various model outputs."""
    if isinstance(proba, pd.DataFrame):
        return proba.iloc[:, 1] if proba.shape[1] > 1 else proba.iloc[:, 0]

    if isinstance(proba, list) and proba and isinstance(proba[0], (list, tuple)):
        return [row[1] if len(row) > 1 else row[0] for row in proba]

    if hasattr(proba, "shape") and len(proba.shape) > 1:
        return proba[:, 1] if proba.shape[1] > 1 else proba[:, 0]

    return proba


def run_prediction(features, model=None):
    """Run model prediction and return a dictionary with results."""
    active_model = model or get_model()
    normalized = normalize_features(features)

    prediction = active_model.predict(normalized)
    result = "Heart Disease Detected" if prediction[0] == 1 else "No Heart Disease Detected"
    body = {"prediction": result}

    if hasattr(active_model, "predict_proba"):
        probability = _extract_probability(active_model.predict_proba(normalized))
        body["probability"] = _to_json_safe(probability)

    return body


def create_app():
    """Flask application factory."""
    app = Flask(__name__)

    @app.get("/health")
    def health():
        try:
            model = get_model()
            return jsonify({"status": "ok", "model_type": type(model).__name__})
        except (ValueError, BotoCoreError, ClientError, pickle.PickleError) as exc:
            return jsonify({"status": "error", "error": str(exc)}), 500

    @app.post("/predict")
    def predict():
        payload = request.get_json(silent=True) or {}
        features = payload.get("features")

        if features is None:
            return (
                jsonify({"error": "Request JSON must include a 'features' field."}),
                400,
            )

        try:
            return jsonify(run_prediction(features))
        except (ValueError, BotoCoreError, ClientError, pickle.PickleError) as exc:
            return jsonify({"error": str(exc)}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
