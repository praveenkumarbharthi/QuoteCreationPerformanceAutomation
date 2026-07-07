@echo off

cd ..

jmeter\apache-jmeter-5.6.3\bin\jmeter.bat ^
-n ^
-t jmeter\createQuote.jmx ^
-l results\result.jtl ^
-e ^
-o reports\HTMLReport

echo Test Finished