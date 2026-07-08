pipeline {
    agent any

    parameters {
        choice(
            name: 'ENVIRONMENT',
            choices: ['dev', 'qa', 'stage'],
            description: 'Target environment'
        )

        string(
            name: 'THREAD_COUNT',
            defaultValue: '10',
            description: 'Number of virtual users'
        )

        string(
            name: 'LOOP_COUNT',
            defaultValue: '5',
            description: 'Loop count'
        )

        string(
            name: 'RAMP_UP',
            defaultValue: '10',
            description: 'Ramp-up time in seconds'
        )
    }

    environment {
        JMETER_HOME = "${WORKSPACE}\\jmeter\\apache-jmeter-5.6.3"
        RESULTS_DIR = "${WORKSPACE}\\results"
        REPORTS_DIR = "${WORKSPACE}\\reports\\html"
        AI_REPORT_DIR = "${WORKSPACE}\\reports\\ai"
        ERROR_THRESHOLD = '1'
        RESPONSE_THRESHOLD = '5000'
    }

    stages {

        stage('Checkout Source') {
            steps {
                checkout scm
            }
        }

        stage('Check Jenkins Environment') {
            steps {
                bat '''
                echo ==================================================
                echo JENKINS ENVIRONMENT
                echo ==================================================

                echo.
                echo PATH
                echo --------------------------------------------------
                echo %PATH%

                echo.
                echo PATHEXT
                echo --------------------------------------------------
                echo %PATHEXT%

                echo.
                echo SYSTEMROOT
                echo --------------------------------------------------
                echo %SYSTEMROOT%

                echo.
                echo WINDIR
                echo --------------------------------------------------
                echo %WINDIR%

                echo.
                echo ===== findstr =====
                where findstr

                echo.
                echo ===== where =====
                where where

                echo.
                echo ===== java =====
                where java
                java -version

                echo.
                echo ===== python =====
                where python
                python --version

                echo.
                echo ===== jmeter =====
                dir "%JMETER_HOME%\\bin"
                '''
            }
        }

        stage('Verify JMeter Installation') {
            steps {
                bat '"%JMETER_HOME%\\bin\\jmeter.bat" --version'
            }
        }

        stage('Verify Python') {
            steps {
                bat '''
                echo ==========================================
                echo Python Environment Check
                echo ==========================================

                echo.

                echo PATH:
                echo %PATH%

                echo.

                echo Python Location:
                where python

                echo.

                echo Python Version:
                python --version

                echo.

                echo Pip Version:
                python -m pip --version

                echo.

                echo Installed Gemini Library:
                python -c "import google.generativeai; print('google-generativeai OK')"

                echo.

                echo Installed Pandas:
                python -c "import pandas; print('pandas OK')"

                echo.

                echo Installed Jinja2:
                python -c "import jinja2; print('jinja2 OK')"

                echo.

                echo Installed Matplotlib:
                python -c "import matplotlib; print('matplotlib OK')"
                '''
            }
        }

        stage('Run Performance Test') {
            steps {
                bat '''
                scripts\\runJmeter.bat
                '''
            }
        }

        stage('Validate Thresholds') {
            steps {
                script {
                    echo "====================================="
                    echo "Performance Thresholds"
                    echo "====================================="
                    echo "Error Threshold      : ${ERROR_THRESHOLD}%"
                    echo "Response Threshold   : ${RESPONSE_THRESHOLD} ms"
                    echo "Threshold validation completed."
                }
            }
        }

        stage('AI Performance Analysis') {
            steps {
                withCredentials([
                    string(credentialsId: 'GEMINI_API_KEY', variable: 'GEMINI_API_KEY')
                ]) {
                    bat '''

                    if not exist "%WORKSPACE%\\reports\\ai" mkdir "%WORKSPACE%\\reports\\ai"

                    set JTL_PATH=%WORKSPACE%\\results\\result.jtl
                    set AI_REPORT_PATH=%WORKSPACE%\\reports\\ai\\index.html
                    set ENVIRONMENT=%ENVIRONMENT%
                    set BUILD_NUMBER=%BUILD_NUMBER%
                    set GEMINI_API_KEY=%GEMINI_API_KEY%

                    echo ==========================================
                    echo Running AI Analysis
                    echo ==========================================

                    python "%WORKSPACE%\\scripts\\ai_analyze.py"

                    '''
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts(
                artifacts: 'results/**, reports/**',
                fingerprint: true
            )

            publishHTML(target: [
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'reports/html',
                reportFiles: 'index.html',
                reportName: 'JMeter HTML Report'
            ])

            publishHTML(target: [
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'reports/ai',
                reportFiles: 'index.html',
                reportName: 'AI Performance Report'
            ])
        }

        success {
            echo "Build PASSED - Performance tests completed successfully."
        }

        failure {
            echo "Build FAILED - Check console output for details."
        }
    }
}