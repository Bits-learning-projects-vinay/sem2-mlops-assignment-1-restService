import json
import os
import pickle

import boto3
import pandas as pd
from botocore.exceptions import BotoCoreError, ClientError

_CACHED_MODEL = None


def load_model_from_s3(bucket_name, object_key, region_name=None, s3_client=None):
	"""Download a pickled model from S3 and deserialize it."""
	client = s3_client or boto3.client("s3", region_name=region_name)
	response = client.get_object(Bucket=bucket_name, Key=object_key)
	model_bytes = response["Body"].read()
	return pickle.loads(model_bytes)




def get_model(s3_client=None):
	"""Load once per warm Lambda container to reduce S3 calls."""
	global _CACHED_MODEL
	if _CACHED_MODEL is not None:
		return _CACHED_MODEL

	bucket = os.environ.get("MODEL_S3_BUCKET")
	key = os.environ.get("MODEL_S3_KEY")
	region = os.environ.get("MODEL_S3_REGION")

	if not bucket or not key:
		raise ValueError("Environment variables MODEL_S3_BUCKET and MODEL_S3_KEY are required.")

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


def lambda_handler(event, context):
	"""
	Lambda entrypoint.
	Optional event payload:
	{
	  "features": [[5.1, 3.5, 1.4, 0.2]]
	}
	"""
	try:
		model = get_model()

		if event and "features" in event:
			features = normalize_features(event["features"])
			prediction = model.predict(features)
			proba = model.predict_proba(features)
			if hasattr(proba, "shape") and len(proba.shape) > 1 and proba.shape[1] > 1:
				probability = proba[:, 1]
			else:
				probability = proba
			prediction_output = prediction.tolist() if hasattr(prediction, "tolist") else prediction
			probability_output = probability.tolist() if hasattr(probability, "tolist") else probability

			body = {"prediction": prediction_output, "probability": probability_output}
		else:
			body = {"message": "Model loaded successfully.", "model_type": type(model).__name__}

		return {"statusCode": 200, "body": json.dumps(body)}

	except (ValueError, BotoCoreError, ClientError, pickle.PickleError) as exc:
		return {
			"statusCode": 500,
			"body": json.dumps({"error": str(exc)}),
		}
