pipeline {

    agent any

    environment {
        JMETER_HOME = "${WORKSPACE}\\jmeter\\apache-jmeter-5.6.3"
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
                bat 'scripts\\runJmeter.bat'
            }
        }

    }

    post {

        always {

            archiveArtifacts artifacts: 'results/*.jtl', fingerprint: true

            publishHTML(target: [
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'reports/html',
                reportFiles: 'index.html',
                reportName: 'JMeter HTML Report'
            ])

        }

    }

}