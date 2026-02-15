@echo off
echo ========================================
echo PlantAI Architecture Diagram Generator
echo ========================================
echo.

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)
echo.

echo Checking diagrams package...
python -c "import diagrams" 2>nul
if errorlevel 1 (
    echo diagrams package not found. Installing...
    pip install diagrams
    if errorlevel 1 (
        echo ERROR: Failed to install diagrams package
        pause
        exit /b 1
    )
)
echo.

echo Checking Graphviz installation...
dot -V 2>nul
if errorlevel 1 (
    echo WARNING: Graphviz not found in PATH
    echo Please install Graphviz from https://graphviz.org/download/
    echo Or use: choco install graphviz
    echo.
    pause
)
echo.

echo ========================================
echo Generating Diagrams...
echo ========================================
echo.

echo [1/3] Generating complete MVP architecture...
python generate_plantai_diagram.py
if errorlevel 1 (
    echo ERROR: Failed to generate complete architecture diagram
) else (
    echo SUCCESS: plantai_mvp_architecture.png created
)
echo.

echo [2/3] Generating simplified architecture...
python generate_plantai_simple_diagram.py
if errorlevel 1 (
    echo ERROR: Failed to generate simplified diagram
) else (
    echo SUCCESS: plantai_mvp_simple.png created
)
echo.

echo [3/3] Generating deployment architecture...
python generate_plantai_deployment_diagram.py
if errorlevel 1 (
    echo ERROR: Failed to generate deployment diagram
) else (
    echo SUCCESS: plantai_deployment.png created
)
echo.

echo ========================================
echo Diagram Generation Complete!
echo ========================================
echo.
echo Generated files:
echo   - plantai_mvp_architecture.png
echo   - plantai_mvp_simple.png
echo   - plantai_deployment.png
echo.
echo You can now view these PNG files in your image viewer.
echo.
pause
