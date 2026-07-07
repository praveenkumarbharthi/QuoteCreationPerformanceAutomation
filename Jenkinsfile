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

        stage('Fix Jenkins CSP') {
            steps {
                script {
                    System.setProperty('hudson.model.DirectoryBrowserSupport.CSP',
                        "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; " +
                        "style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:;")
                }
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
            archiveArtifacts artifacts: 'results/**, reports/**', fingerprint: true
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
