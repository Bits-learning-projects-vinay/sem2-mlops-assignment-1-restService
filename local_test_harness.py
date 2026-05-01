import io
import os
import pickle
from unittest.mock import Mock, patch

import lambda_function


def run_local_test():
	os.environ["MODEL_S3_BUCKET"] = "demo-bucket"
	os.environ["MODEL_S3_KEY"] = "models/demo.pkl"
	os.environ["MODEL_S3_REGION"] = "us-east-1"

	fake_model = {"model_name": "demo"}
	fake_payload = pickle.dumps(fake_model)

	mocked_s3 = Mock()
	mocked_s3.get_object.return_value = {"Body": io.BytesIO(fake_payload)}

	lambda_function._CACHED_MODEL = None
	with patch("modelRestService.boto3.client", return_value=mocked_s3):
		result = lambda_function.lambda_handler({}, None)

	print(result)


if __name__ == "__main__":
	run_local_test()

