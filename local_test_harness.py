import io
import os
import pickle
from unittest.mock import Mock, patch

import model_service


class FakeModel:
    def predict(self, features):
        rows = len(features) if hasattr(features, "__len__") else 1
        return [1] * rows

    def predict_proba(self, features):
        rows = len(features) if hasattr(features, "__len__") else 1
        return [[0.2, 0.8] for _ in range(rows)]


def run_local_test():
    os.environ["MODEL_S3_BUCKET"] = "demo-bucket"
    os.environ["MODEL_S3_KEY"] = "models/demo.pkl"
    os.environ["MODEL_S3_REGION"] = "ap-south-1"

    fake_payload = pickle.dumps(FakeModel())
    mocked_s3 = Mock()
    mocked_s3.get_object.return_value = {"Body": io.BytesIO(fake_payload)}

    model_service._CACHED_MODEL = None
    app = model_service.create_app()

    with patch("model_service.boto3.client", return_value=mocked_s3):
        client = app.test_client()

        health_response = client.get("/health")
        predict_response = client.post(
            "/predict",
            json={
                "features": [
                    {
                        "age": 63,
                        "sex": 1,
                        "cp": 3,
                        "trestbps": 145,
                        "chol": 233,
                        "fbs": 1,
                        "restecg": 0,
                        "thalach": 150,
                        "exang": 0,
                        "oldpeak": 2.3,
                        "slope": 0,
                        "ca": 0,
                        "thal": "?",
                    }
                ]
            },
        )

    print("health:", health_response.status_code, health_response.get_json())
    print("predict:", predict_response.status_code, predict_response.get_json())


if __name__ == "__main__":
    run_local_test()

