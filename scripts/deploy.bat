@echo off
setlocal enabledelayedexpansion

REM ====== INPUTS ======
set Environment=%1
set ProjectName=%2

if "%Environment%"=="" set Environment=dev
if "%ProjectName%"=="" set ProjectName=twin

echo Deploying %ProjectName% to %Environment% ...

REM ====== GO TO PROJECT ROOT ======
cd /d "%~dp0.."

REM ====== 1. BUILD LAMBDA ======
echo.
echo ====== CHECKING LAMBDA PACKAGE ======
cd backend

if exist lambda-deployment.zip (
    echo lambda-deployment.zip found. Skipping Lambda package build.
) else (
    echo lambda-deployment.zip not found. Building Lambda package...

    if not exist pyproject.toml (
        echo Initializing uv project...
        call uv init
    )

    if exist requirements.txt (
        echo Installing dependencies from requirements.txt...
        call uv add -r requirements.txt
    )

    echo Syncing uv environment...
    call uv sync
    if errorlevel 1 (
        echo uv sync failed!
        exit /b 1
    )

    echo Running Lambda package script...
    call uv run deploy.py
    if errorlevel 1 (
        echo Lambda package script failed!
        exit /b 1
    )
)

cd ..

REM ====== 2. TERRAFORM ======
echo.
echo ====== RUNNING TERRAFORM ======
cd terraform

call terraform init -input=false
if errorlevel 1 (
    echo Terraform init failed!
    exit /b 1
)

echo Selecting workspace %Environment%...
call terraform workspace select %Environment% >nul 2>&1
if errorlevel 1 (
    echo Workspace not found. Creating new workspace...
    call terraform workspace new %Environment%
)

echo Current workspace:
terraform workspace show

if "%Environment%"=="prod" (
    call terraform apply -var-file=prod.tfvars -var="project_name=%ProjectName%" -var="environment=%Environment%" -auto-approve
) else (
    call terraform apply -var="project_name=%ProjectName%" -var="environment=%Environment%" -auto-approve
)

if errorlevel 1 (
    echo Terraform apply failed!
    exit /b 1
)

for /f %%i in ('terraform output -raw api_gateway_url') do set ApiUrl=%%i
for /f %%i in ('terraform output -raw s3_frontend_bucket') do set FrontendBucket=%%i
for /f %%i in ('terraform output -raw custom_domain_url 2^>nul') do set CustomUrl=%%i
for /f %%i in ('terraform output -raw cloudfront_url') do set CfUrl=%%i

cd ..

REM ====== 3. FRONTEND ======
echo.
echo ====== BUILDING FRONTEND ======
cd frontend

echo Setting API URL for production build...
echo REACT_APP_API_URL=%ApiUrl% > .env.production

echo Installing frontend dependencies...
call npm install --no-audit --no-fund

echo Building React app...
call npm run build
if errorlevel 1 (
    echo React build failed!
    exit /b 1
)

echo Uploading frontend build to S3...
aws s3 sync .\build s3://%FrontendBucket%/ --delete
if errorlevel 1 (
    echo S3 upload failed!
    exit /b 1
)

cd ..

REM ====== 4. SUMMARY ======
echo.
echo Deployment complete!
echo CloudFront URL : %CfUrl%
if defined CustomUrl echo Custom domain  : %CustomUrl%
echo API Gateway    : %ApiUrl%

endlocal