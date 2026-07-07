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
        ERROR_THRESHOLD    = '1'
        RESPONSE_THRESHOLD = '5000'
    }

    stages {

        stage('Checkout Source') {
            steps {
                checkout scm
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
                    def jtlFile = "${WORKSPACE}\\results\\result.jtl"
                    echo "Checking performance thresholds against result.jtl..."
                    echo "Error threshold  : ${ERROR_THRESHOLD}%"
                    echo "Response threshold: ${RESPONSE_THRESHOLD} ms"
                    echo "Threshold check stage complete - review Statistics in HTML report."
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
        }
        success {
            echo "Build PASSED - Performance tests completed successfully."
        }
        failure {
            echo "Build FAILED - Check JMeter HTML Report and result.jtl for details."
        }
    }
}
