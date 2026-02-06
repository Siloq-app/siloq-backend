@echo off
REM Setup script for Siloq Django Backend (Windows)

echo Setting up Siloq Django Backend...

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check if .env exists
if not exist ".env" (
    echo Creating .env file from .env.example...
    copy .env.example .env
    echo Please edit .env file with your settings!
)

REM Run migrations
echo Running migrations...
python manage.py migrate

REM Create superuser
echo Creating superuser...
python manage.py createsuperuser

echo Setup complete!
echo Run 'venv\Scripts\activate.bat' to activate virtual environment
echo Run 'python manage.py runserver' to start development server

pause
