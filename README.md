# AWS Lambda Model Loader

This project includes an AWS Lambda handler in `modelRestService.py` that reads a pickled model from an S3 bucket.

## Required environment variables

- `MODEL_S3_BUCKET`: S3 bucket name
- `MODEL_S3_KEY`: S3 object key for the `.pkl` model file
- `MODEL_S3_REGION` (optional): AWS region for S3 client

## Lambda event format

You can call the function with an empty event to just verify model loading:

```json
{}
```

If your model supports `.predict(...)`, pass features as a list of rows or a list of records.

```json
{
  "features": [[5.1, 3.5, 1.4, 0.2]]
}
```

Heart-disease record example (DataFrame-style input):

```json
{
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
      "thal": "?"
    }
  ]
}
```

## Local test (no AWS credentials required)

`local_test_harness.py` mocks S3 and validates the Lambda handler end-to-end.

```powershell
python -m pip install -r requirements.txt
python local_test_harness.py
```

## Deploy as AWS Lambda service

### Prerequisites

- AWS CLI configured (`aws configure`)
- A Lambda execution role ARN with at least CloudWatch Logs + S3 read permissions
- `MODEL_S3_BUCKET`, `MODEL_S3_KEY`, and `MODEL_S3_REGION` available in your shell (or `.env` loaded)

### Deploy from local machine (PowerShell)

```powershell
python -m pip install -r requirements.txt
$env:MODEL_S3_BUCKET="mlops-assignment1-vin"
$env:MODEL_S3_KEY="model/heart_disease_logistic_regression_pipeline.pkl"
$env:MODEL_S3_REGION="ap-south-1"
.\scripts\deploy-lambda.ps1 -FunctionName "heart-disease-model-service" -Region "ap-south-1" -RoleArn "<your-lambda-role-arn>"
```

If the function already exists, the script updates code. If it does not exist, the script creates it.

### Deploy from GitHub Actions

Workflow file: `.github/workflows/deploy-lambda.yml`

Add these repository secrets:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `LAMBDA_FUNCTION_NAME`
- `LAMBDA_ROLE_ARN`
- `MODEL_S3_BUCKET`
- `MODEL_S3_KEY`
- `MODEL_S3_REGION`

Then trigger **Deploy Lambda** from the Actions tab or push to `main`.

### Invoke test event

```json
{
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
      "thal": "?"
    }
  ]
}
```

