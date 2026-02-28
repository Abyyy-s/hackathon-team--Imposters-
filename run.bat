@echo off
echo.
echo  LifeLink AI — Blood Emergency Response System
echo ================================================
pip install flask flask-cors
echo.
set /p APIKEY="Enter your Gemini API key (aistudio.google.com): "
if not "%APIKEY%"=="" (
  set GEMINI_API_KEY=%APIKEY%
  echo Gemini AI activated!
) else (
  echo No key — using smart fallback logic
)
echo.
echo Starting server...
echo Open http://localhost:5000 in your browser
echo.
python app.py
pause
