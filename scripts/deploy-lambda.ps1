param(
    [Parameter(Mandatory = $false)]
    [string]$FunctionName = "heart-disease-model-service",

    [Parameter(Mandatory = $false)]
    [string]$Region = "ap-south-1",

    [Parameter(Mandatory = $false)]
    [string]$Handler = "modelRestService.lambda_handler",

    [Parameter(Mandatory = $false)]
    [string]$Runtime = "python3.11",

    [Parameter(Mandatory = $false)]
    [string]$RoleArn = "",

    [Parameter(Mandatory = $false)]
    [string]$RequirementsFile = "requirements.lambda.txt"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$packageDir = Join-Path $projectRoot "build\lambda-package"
$zipPath = Join-Path $projectRoot "build\lambda.zip"

if (Test-Path $packageDir) {
    Remove-Item -Recurse -Force $packageDir
}
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

New-Item -ItemType Directory -Path $packageDir -Force | Out-Null

python -m pip install --upgrade pip
python -m pip install -r (Join-Path $projectRoot $RequirementsFile) -t $packageDir
Copy-Item (Join-Path $projectRoot "modelRestService.py") $packageDir -Force

Push-Location $packageDir
Compress-Archive -Path * -DestinationPath $zipPath
Pop-Location

$exists = $false
try {
    aws lambda get-function --function-name $FunctionName --region $Region | Out-Null
    $exists = $true
}
catch {
    $exists = $false
}

if ($exists) {
    aws lambda update-function-code --function-name $FunctionName --zip-file ("fileb://" + $zipPath) --region $Region | Out-Null
}
else {
    if (-not $RoleArn) {
        throw "RoleArn is required when creating a new Lambda function."
    }

    aws lambda create-function `
        --function-name $FunctionName `
        --runtime $Runtime `
        --handler $Handler `
        --role $RoleArn `
        --zip-file ("fileb://" + $zipPath) `
        --timeout 30 `
        --memory-size 512 `
        --region $Region | Out-Null
}

if (-not $env:MODEL_S3_BUCKET -or -not $env:MODEL_S3_KEY) {
    Write-Warning "MODEL_S3_BUCKET or MODEL_S3_KEY not set in current shell. Skipping Lambda environment update."
}
else {
    $variables = "{MODEL_S3_BUCKET=$($env:MODEL_S3_BUCKET),MODEL_S3_KEY=$($env:MODEL_S3_KEY),MODEL_S3_REGION=$($env:MODEL_S3_REGION)}"
    aws lambda update-function-configuration --function-name $FunctionName --environment ("Variables=" + $variables) --region $Region | Out-Null
}

Write-Host "Deployment complete for Lambda function: $FunctionName in region: $Region"

