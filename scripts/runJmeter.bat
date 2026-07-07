@echo off

cd ..

jmeter\apache-jmeter-5.6.3\bin\jmeter.bat ^
-n ^
-t jmeter\createQuote.jmx ^
-l results\result.jtl ^
-e ^
-o reports\HTMLReport

IF %ERRORLEVEL% NEQ 0 EXIT /B %ERRORLEVEL%

echo Test Finished