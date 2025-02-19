@echo off

python -m pip show virtualenv >nul 2>&1

if %errorlevel% equ 0 (
    echo Package 'virtualenv' installed.
)
if not %errorlevel% equ 0 (
    echo Package 'virtualenv' not installed.
    echo Installing now...
    python -m pip install virtualenv
)

::Check if .venv exists
if not exist ".venv\" (
    echo Virtual environment .venv not found.
    echo Installing virtual envitonment...

)
if exist ".venv\" (
    echo Virtual environment .venv found.
)

echo Activating .venv...
call .venv\Scripts\activate.bat

echo Installing packages from requirements.txt...
python -m pip install -r requirements.txt

echo Launching application...
python src\abbreviation_labeler.py

deactivate