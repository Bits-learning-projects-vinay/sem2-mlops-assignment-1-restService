import os
import pickle
import logging  # Added for request and result logging

import boto3
import pandas as pd
from flask import Flask, jsonify, request
from prometheus_client import CollectorRegistry
from prometheus_flask_exporter import PrometheusMetrics  # Added for monitoring metrics

# 1. Configure Logging
# Using INFO level to capture predictions and request statuses in Docker logs
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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
        logger.error(
            "Environment variables MODEL_S3_BUCKET and MODEL_S3_KEY are missing."
        )
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

    # Specific logging for heart disease detection results
    if prediction[0] == 1:
        result = "Heart Disease Detected"
        logger.info(f"PREDICTION RESULT: {result} - Patient identified as high risk.")
    else:
        result = "No Heart Disease Detected"
        logger.info(f"PREDICTION RESULT: {result} - Patient identified as low risk.")

    body = {"prediction": result}

    if hasattr(active_model, "predict_proba"):
        probability = _extract_probability(active_model.predict_proba(normalized))
        body["probability"] = _to_json_safe(probability)
        logger.info(f"Model Probability: {body['probability']}")

    return body


def create_app():
    """Flask application factory."""
    app = Flask(__name__)

    # Use an app-local registry so repeated app factory calls do not clash in tests.
    metrics = PrometheusMetrics(app, registry=CollectorRegistry())
    metrics.info("app_info", "Model Service Info", version="1.0.0")

    # 3. Global Request Logging
    @app.before_request
    def log_request_info():
        logger.info(
            f"Incoming: {request.method} {request.path} from {request.remote_addr}"
        )

    @app.after_request
    def log_response_info(response):
        logger.info(f"Outgoing: {response.status}")
        return response

    @app.get("/health")
    def health():
        try:
            model = get_model()
            return jsonify({"status": "ok", "model_type": type(model).__name__})
        except Exception as exc:
            logger.exception("Health check failed")
            return jsonify({"status": "error", "error": str(exc)}), 500

    @app.post("/predict")
    def predict():
        payload = request.get_json(silent=True) or {}
        features = payload.get("features")

        if features is None:
            logger.warning("Predict called without 'features' key in JSON")
            return (
                jsonify({"error": "Request JSON must include a 'features' field."}),
                400,
            )

        try:
            return jsonify(run_prediction(features))
        except Exception as exc:
            logger.exception("Prediction processing error")
            return jsonify({"error": str(exc)}), 500

    return app


app = create_app()


if __name__ == "__main__":
    # The PORT environment variable is used primarily for containerized environments
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
