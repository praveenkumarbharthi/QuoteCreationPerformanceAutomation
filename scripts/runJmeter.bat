@echo off

echo ==========================================
echo Running JMeter Performance Test
echo ==========================================

REM Create folders if they don't exist

if not exist results mkdir results
if not exist reports mkdir reports

REM Execute JMeter

jmeter\apache-jmeter-5.6.3\bin\jmeter.bat ^
-n ^
-t jmeter\createQuote.jmx ^
-l results\result.jtl ^
-e ^
-o reports\html

IF %ERRORLEVEL% NEQ 0 EXIT /B %ERRORLEVEL%

echo.
echo ==========================================
echo Test Finished Successfully
echo ==========================================