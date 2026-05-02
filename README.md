# Flask Model Service (S3 PKL Loader)

This project runs a Flask API on EC2. It loads a pickled ML model from S3 and serves prediction requests.

## Files

- `model_service.py`: Flask app (`/health`, `/predict`) and S3 model loader
- `local_test_harness.py`: local mock test without real AWS credentials
- `.github/workflows/deploy-lambda.yml`: GitHub Actions workflow that deploys to EC2
- `scripts/ec2_bootstrap.sh`: creates systemd service with Gunicorn on EC2

## Required environment variables

- `MODEL_S3_BUCKET`: S3 bucket name
- `MODEL_S3_KEY`: S3 object key for your `.pkl` file
- `MODEL_S3_REGION` (optional): defaults to your boto/AWS config
- `PORT` (optional): defaults to `8000`

## Run locally

```powershell
python -m pip install -r requirements.txt
$env:MODEL_S3_BUCKET="mlops-assignment1-vin"
$env:MODEL_S3_KEY="model/heart_disease_logistic_regression_pipeline.pkl"
$env:MODEL_S3_REGION="ap-south-1"
python model_service.py
```

Test endpoints:

```powershell
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/predict -H "Content-Type: application/json" -d '{"features":[{"age":63,"sex":1,"cp":3,"trestbps":145,"chol":233,"fbs":1,"restecg":0,"thalach":150,"exang":0,"oldpeak":2.3,"slope":0,"ca":0,"thal":"?"}]}'
```

## Local mock test (no AWS creds)

```powershell
python local_test_harness.py
```

## Deploy to EC2 manually

1. Copy `model_service.py` and `requirements.txt` to EC2 (for example `/opt/model-service`).
2. On EC2, set environment variables and run bootstrap script.

```bash
export APP_DIR=/opt/model-service
export APP_USER=ubuntu
export MODEL_S3_BUCKET=mlops-assignment1-vin
export MODEL_S3_KEY=model/heart_disease_logistic_regression_pipeline.pkl
export MODEL_S3_REGION=ap-south-1
bash scripts/ec2_bootstrap.sh
```

The service is started as `model-service` and bound to `0.0.0.0:8000`.

### Deploy from Windows (PowerShell)

```powershell
$env:MODEL_S3_BUCKET="mlops-assignment1-vin"
$env:MODEL_S3_KEY="model/heart_disease_logistic_regression_pipeline.pkl"
$env:MODEL_S3_REGION="ap-south-1"
.\scripts\deploy-ec2.ps1 -Ec2Host "<ec2-public-ip-or-dns>" -Ec2User "ubuntu" -SshKeyPath "C:\path\to\key.pem"
```

## Deploy to EC2 with GitHub Actions

Workflow: `.github/workflows/deploy-lambda.yml` (renamed behavior: EC2 deploy)

Add repository secrets:

- `EC2_HOST`
- `EC2_USER`
- `EC2_SSH_KEY`
- `EC2_PORT` (for example `22`)
- `EC2_APP_DIR` (for example `/opt/model-service`)
- `MODEL_S3_BUCKET`
- `MODEL_S3_KEY`
- `MODEL_S3_REGION`

Then trigger the workflow from Actions tab or push to `main`.

