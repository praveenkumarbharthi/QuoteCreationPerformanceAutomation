@echo off

echo ==========================================
echo Running JMeter Performance Test
echo ==========================================

REM Delete previous report
if exist reports rmdir /S /Q reports

REM Delete previous results
if exist results rmdir /S /Q results

REM Create folders
mkdir reports
mkdir results

REM Execute JMeter

jmeter\apache-jmeter-5.6.3\bin\jmeter.bat ^
-n ^
-t jmeter\createQuote.jmx ^
-l results\result.jtl ^
-j results\jmeter.log ^
-e ^
-o reports\html

IF %ERRORLEVEL% NEQ 0 EXIT /B %ERRORLEVEL%

echo.
echo ==========================================
echo Test Finished Successfully
echo ==========================================