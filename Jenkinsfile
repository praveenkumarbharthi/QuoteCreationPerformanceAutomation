pipeline {
    agent any

    environment {
        JMETER_HOME = 'C:\\Users\\Praveen_Kumar\\Desktop\\Jmeter\\apache-jmeter-5.6.3'
    }

    stages {

        stage('Checkout Source') {
            steps {
                checkout scm
            }
        }

        stage('Verify JMeter') {
            steps {
                bat '"%JMETER_HOME%\\bin\\jmeter.bat" --version'
            }
        }

        stage('Run JMeter Test') {
            steps {
                bat '''
                if not exist results mkdir results
                if not exist reports mkdir reports

                "%JMETER_HOME%\\bin\\jmeter.bat" ^
                -n ^
                -t jmeter\\createQuote.jmx ^
                -l results\\result.jtl ^
                -e ^
                -o reports\\html
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'results/*.jtl', fingerprint: true

            publishHTML(target: [
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'reports/html',
                reportFiles: 'index.html',
                reportName: 'JMeter HTML Report'
            ])
        }
    }
}