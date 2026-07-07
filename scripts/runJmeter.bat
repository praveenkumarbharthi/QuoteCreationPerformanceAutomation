@echo off
setlocal

echo ==========================================
echo Running JMeter Performance Test
echo ==========================================

REM Move to project root regardless of where Jenkins starts this script
cd /d "%~dp0.."

echo.
echo ==========================================
echo Current Working Directory
echo ==========================================
cd

echo.
echo ==========================================
echo Project Files
echo ==========================================
dir

echo.
echo ==========================================
echo Cleaning Previous Results
echo ==========================================

if exist reports rmdir /S /Q reports
if exist results rmdir /S /Q results

mkdir reports
mkdir results

echo.
echo ==========================================
echo Running JMeter...
echo ==========================================

jmeter\apache-jmeter-5.6.3\bin\jmeter.bat ^
-n ^
-t jmeter\createQuote.jmx ^
-l results\result.jtl ^
-j results\jmeter.log ^
-e ^
-o reports\html

set EXITCODE=%ERRORLEVEL%

echo.
echo ==========================================
echo JMeter Exit Code = %EXITCODE%
echo ==========================================

echo.
echo ==========================================
echo Results Folder
echo ==========================================
dir results

echo.
echo ==========================================
echo Reports Folder
echo ==========================================
dir reports

exit /b %EXITCODE%