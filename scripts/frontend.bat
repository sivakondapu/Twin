@echo off
setlocal

cd /d "%~dp0.."
cd frontend

echo.
echo ===== STEP 1: INSTALL DEPENDENCIES =====
call npm install --no-audit --no-fund

echo.
echo ===== STEP 2: BUILD REACT APP =====
call npm run build
if errorlevel 1 (
    echo React build failed!
    exit /b 1
)

echo.
echo ===== STEP 3: UPLOAD BUILD TO S3 =====
aws s3 sync .\build s3://sivatest1980/ --delete
if errorlevel 1 (
    echo S3 upload failed!
    exit /b 1
)

echo.
echo Deployment complete!

endlocal