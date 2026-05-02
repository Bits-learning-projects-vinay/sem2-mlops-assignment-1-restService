param(
    [Parameter(Mandatory = $true)]
    [string]$Ec2Host,

    [Parameter(Mandatory = $false)]
    [string]$Ec2User = "ubuntu",

    [Parameter(Mandatory = $true)]
    [string]$SshKeyPath,

    [Parameter(Mandatory = $false)]
    [int]$Port = 22,

    [Parameter(Mandatory = $false)]
    [string]$AppDir = "/opt/model-service"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$modelFile = Join-Path $projectRoot "model_service.py"
$requirementsFile = Join-Path $projectRoot "requirements.txt"
$bootstrapFile = Join-Path $projectRoot "scripts/ec2_bootstrap.sh"

if (-not $env:MODEL_S3_BUCKET -or -not $env:MODEL_S3_KEY) {
    throw "Set MODEL_S3_BUCKET and MODEL_S3_KEY in your shell before running this script."
}

ssh -i $SshKeyPath -p $Port "${Ec2User}@${Ec2Host}" "mkdir -p ${AppDir}"

scp -i $SshKeyPath -P $Port $modelFile "${Ec2User}@${Ec2Host}:${AppDir}/model_service.py"
scp -i $SshKeyPath -P $Port $requirementsFile "${Ec2User}@${Ec2Host}:${AppDir}/requirements.txt"
scp -i $SshKeyPath -P $Port $bootstrapFile "${Ec2User}@${Ec2Host}:${AppDir}/ec2_bootstrap.sh"

$remoteScript = @"
set -e
mkdir -p ${AppDir}
chmod +x ${AppDir}/ec2_bootstrap.sh
cd ${AppDir}
export MODEL_S3_BUCKET='${env:MODEL_S3_BUCKET}'
export MODEL_S3_KEY='${env:MODEL_S3_KEY}'
export MODEL_S3_REGION='${env:MODEL_S3_REGION}'
export APP_DIR='${AppDir}'
export APP_USER='${Ec2User}'
bash ./ec2_bootstrap.sh
"@

ssh -i $SshKeyPath -p $Port "${Ec2User}@${Ec2Host}" $remoteScript

Write-Host "EC2 deployment completed on ${Ec2Host}."

