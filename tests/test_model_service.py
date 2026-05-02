import io
import os
import pickle
import unittest
from unittest.mock import Mock, patch

import pandas as pd

import model_service


class DummyModelWithProba:
    def __init__(self):
        self.seen_features = None

    def predict(self, features):
        self.seen_features = features
        return [1]

    def predict_proba(self, features):
        self.seen_features = features
        return [[0.2, 0.8]]


class DummyModelNoProba:
    def predict(self, features):
        return [0]


class ModelServiceUnitTests(unittest.TestCase):
    def setUp(self):
        self._old_cache = model_service._CACHED_MODEL
        model_service._CACHED_MODEL = None

        self._saved_env = {
            "MODEL_S3_BUCKET": os.environ.get("MODEL_S3_BUCKET"),
            "MODEL_S3_KEY": os.environ.get("MODEL_S3_KEY"),
            "MODEL_S3_REGION": os.environ.get("MODEL_S3_REGION"),
        }

    def tearDown(self):
        model_service._CACHED_MODEL = self._old_cache
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_load_model_from_s3_downloads_and_unpickles(self):
        expected_model = {"model": "ok"}
        body = io.BytesIO(pickle.dumps(expected_model))
        s3_client = Mock()
        s3_client.get_object.return_value = {"Body": body}

        actual = model_service.load_model_from_s3(
            bucket_name="demo-bucket",
            object_key="models/demo.pkl",
            s3_client=s3_client,
        )

        self.assertEqual(expected_model, actual)
        s3_client.get_object.assert_called_once_with(Bucket="demo-bucket", Key="models/demo.pkl")

    def test_get_model_raises_when_required_env_missing(self):
        os.environ.pop("MODEL_S3_BUCKET", None)
        os.environ.pop("MODEL_S3_KEY", None)

        with self.assertRaises(ValueError):
            model_service.get_model()

    def test_get_model_caches_download_result(self):
        os.environ["MODEL_S3_BUCKET"] = "bucket"
        os.environ["MODEL_S3_KEY"] = "key"
        os.environ["MODEL_S3_REGION"] = "ap-south-1"

        loaded_model = object()
        with patch("model_service.load_model_from_s3", return_value=loaded_model) as mocked_loader:
            first = model_service.get_model()
            second = model_service.get_model()

        self.assertIs(first, loaded_model)
        self.assertIs(second, loaded_model)
        mocked_loader.assert_called_once_with(
            bucket_name="bucket",
            object_key="key",
            region_name="ap-south-1",
            s3_client=None,
        )

    def test_normalize_features_converts_list_of_dict_to_dataframe(self):
        features = [{"age": 63, "thal": "?"}]

        normalized = model_service.normalize_features(features)

        self.assertIsInstance(normalized, pd.DataFrame)
        self.assertEqual(normalized.iloc[0]["age"], 63)
        self.assertEqual(normalized.iloc[0]["thal"], "?")

    def test_extract_probability_for_nested_list_picks_positive_class(self):
        probability = model_service._extract_probability([[0.9, 0.1], [0.3, 0.7]])

        self.assertEqual(probability, [0.1, 0.7])

    def test_run_prediction_with_proba_returns_prediction_and_probability(self):
        model = DummyModelWithProba()
        features = [{"age": 63, "thal": "?"}]

        result = model_service.run_prediction(features, model=model)

        self.assertEqual(result["prediction"], [1])
        self.assertEqual(result["probability"], [0.8])
        self.assertIsInstance(model.seen_features, pd.DataFrame)

    def test_run_prediction_without_predict_proba_returns_prediction_only(self):
        model = DummyModelNoProba()

        result = model_service.run_prediction([[1, 2, 3]], model=model)

        self.assertEqual(result, {"prediction": [0]})


class FlaskRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = model_service.create_app().test_client()

    def test_health_success(self):
        with patch("model_service.get_model", return_value=DummyModelWithProba()):
            response = self.app.get("/health")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["status"], "ok")
        self.assertIn("model_type", body)

    def test_health_error(self):
        with patch("model_service.get_model", side_effect=ValueError("missing env")):
            response = self.app.get("/health")

        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["status"], "error")
        self.assertIn("missing env", body["error"])

    def test_predict_requires_features(self):
        response = self.app.post("/predict", json={})

        self.assertEqual(response.status_code, 400)
        self.assertIn("features", response.get_json()["error"])

    def test_predict_success(self):
        expected = {"prediction": [1], "probability": [0.8]}
        with patch("model_service.run_prediction", return_value=expected):
            response = self.app.post("/predict", json={"features": [[1, 2, 3]]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), expected)

    def test_predict_error(self):
        with patch("model_service.run_prediction", side_effect=ValueError("bad input")):
            response = self.app.post("/predict", json={"features": [[1, 2, 3]]})

        self.assertEqual(response.status_code, 500)
        self.assertIn("bad input", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()

