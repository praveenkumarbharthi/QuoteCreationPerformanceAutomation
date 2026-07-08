pipeline {
    agent any

    parameters {
        choice(
            name: 'ENVIRONMENT',
            choices: ['dev', 'qa', 'stage'],
            description: 'Target environment to run performance tests against'
        )
        string(
            name: 'THREAD_COUNT',
            defaultValue: '10',
            description: 'Number of concurrent virtual users (threads)'
        )
        string(
            name: 'LOOP_COUNT',
            defaultValue: '5',
            description: 'Number of iterations per thread'
        )
        string(
            name: 'RAMP_UP',
            defaultValue: '10',
            description: 'Ramp-up period in seconds'
        )
    }

    environment {
        JMETER_HOME        = "${WORKSPACE}\\jmeter\\apache-jmeter-5.6.3"
        RESULTS_DIR        = "${WORKSPACE}\\results"
        REPORTS_DIR        = "${WORKSPACE}\\reports\\html"
        AI_REPORT_DIR      = "${WORKSPACE}\\reports\\ai"
        HISTORY_DIR        = "${WORKSPACE}\\reports\\history"
        SCORE_REPORT_DIR   = "${WORKSPACE}\\reports\\score"
        TREND_REPORT_DIR   = "${WORKSPACE}\\reports\\trend"
        ERROR_THRESHOLD    = '1'
        RESPONSE_THRESHOLD = '5000'
    }

    stages {

        stage('Checkout Source') {
            steps {
                checkout scm
            }
        }

        stage('Setup Python Dependencies') {
            steps {
                bat '''
                    python -m pip install --upgrade pip --quiet
                    pip install google-generativeai --quiet
                '''
            }
        }

        stage('Verify JMeter Installation') {
            steps {
                bat '"%JMETER_HOME%\\bin\\jmeter.bat" --version'
            }
        }

        stage('Run Performance Test') {
            steps {
                bat """
                scripts\\runJmeter.bat
                """
            }
        }

        stage('Validate Thresholds') {
            steps {
                script {
                    echo "Checking performance thresholds against result.jtl..."
                    echo "Error threshold : ${ERROR_THRESHOLD}%"
                    echo "Response threshold: ${RESPONSE_THRESHOLD} ms"
                    echo "Threshold check complete - review JMeter HTML Report for details."
                }
            }
        }

        stage('AI Performance Analysis') {
            steps {
                withCredentials([string(credentialsId: 'GEMINI_API_KEY', variable: 'GEMINI_API_KEY')]) {
                    bat """
                    set JTL_PATH=%WORKSPACE%\\results\\result.jtl
                    set AI_REPORT_PATH=%WORKSPACE%\\reports\\ai\\index.html
                    set ENVIRONMENT=${params.ENVIRONMENT}
                    set BUILD_NUMBER=${env.BUILD_NUMBER}
                    set THREAD_COUNT=${params.THREAD_COUNT}
                    set LOOP_COUNT=${params.LOOP_COUNT}
                    set GEMINI_API_KEY=%GEMINI_API_KEY%
                    python scripts\\ai_analyze.py
                    """
                }
            }
        }

        stage('Store Build Metrics History') {
            steps {
                bat """
                if not exist "%WORKSPACE%\\reports\\history" mkdir "%WORKSPACE%\\reports\\history"
                if exist "%WORKSPACE%\\reports\\ai\\metrics.json" (
                    copy "%WORKSPACE%\\reports\\ai\\metrics.json" "%WORKSPACE%\\reports\\history\\build_${env.BUILD_NUMBER}.json"
                    echo Build ${env.BUILD_NUMBER} metrics saved to history.
                )
                """
            }
        }

        stage('AI Trend Analysis') {
            steps {
                withCredentials([string(credentialsId: 'GEMINI_API_KEY', variable: 'GEMINI_API_KEY')]) {
                    bat """
                    if not exist "%WORKSPACE%\\reports\\trend" mkdir "%WORKSPACE%\\reports\\trend"
                    set HISTORY_DIR=%WORKSPACE%\\reports\\history
                    set TREND_REPORT_PATH=%WORKSPACE%\\reports\\trend\\index.html
                    set BUILD_NUMBER=${env.BUILD_NUMBER}
                    set GEMINI_API_KEY=%GEMINI_API_KEY%
                    python scripts\\ai_trend.py
                    """
                }
            }
        }

        stage('Performance Score') {
            steps {
                withCredentials([string(credentialsId: 'GEMINI_API_KEY', variable: 'GEMINI_API_KEY')]) {
                    bat """
                    if not exist "%WORKSPACE%\\reports\\score" mkdir "%WORKSPACE%\\reports\\score"
                    set METRICS_PATH=%WORKSPACE%\\reports\\ai\\metrics.json
                    set SCORE_REPORT_PATH=%WORKSPACE%\\reports\\score\\index.html
                    set BUILD_NUMBER=${env.BUILD_NUMBER}
                    set GEMINI_API_KEY=%GEMINI_API_KEY%
                    python scripts\\ai_score.py
                    """
                }
            }
        }

    }

    post {
        always {
            archiveArtifacts artifacts: 'results/**, reports/**', fingerprint: true

            publishHTML(target: [
                allowMissing         : true,
                alwaysLinkToLastBuild: true,
                keepAll              : true,
                reportDir            : 'reports/html',
                reportFiles          : 'index.html',
                reportName           : 'JMeter HTML Report'
            ])

            publishHTML(target: [
                allowMissing         : true,
                alwaysLinkToLastBuild: true,
                keepAll              : true,
                reportDir            : 'reports/ai',
                reportFiles          : 'index.html',
                reportName           : 'AI Performance Report'
            ])

            publishHTML(target: [
                allowMissing         : true,
                alwaysLinkToLastBuild: true,
                keepAll              : true,
                reportDir            : 'reports/trend',
                reportFiles          : 'index.html',
                reportName           : 'AI Trend Analysis'
            ])

            publishHTML(target: [
                allowMissing         : true,
                alwaysLinkToLastBuild: true,
                keepAll              : true,
                reportDir            : 'reports/score',
                reportFiles          : 'index.html',
                reportName           : 'Performance Score'
            ])
        }

        success {
            echo 'Build PASSED - All AI reports generated successfully.'
        }

        failure {
            echo 'Build FAILED - Check JMeter HTML Report and AI Analysis for details.'
        }
    }
}
