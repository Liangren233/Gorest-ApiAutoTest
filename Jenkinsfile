pipeline {
    agent any

    environment {
        GOREST_TOKEN = credentials('gorest-token')
        WECHAT_WEBHOOK = credentials('wechat-webhook')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup Python') {
            steps {
                bat 'python --version'
                bat 'pip install -r requirements.txt'
            }
        }

        stage('Run Tests') {
            steps {
                bat 'pytest --env=test --alluredir=report/tmp -v'
            }
        }

        stage('Allure Report') {
            steps {
                script {
                    allure includeProperties: false, jdk: '', results: [[path: 'report/tmp']]
                }
            }
        }
    }

    post {
        success {
            script {
                // 将精确耗时和链接注入环境变量后调用 Python
                bat 'set BUILD_DURATION_STR=' + currentBuild.durationString + ' && python notify.py "%WECHAT_WEBHOOK%" success'
            }
        }
        failure {
            script {
                bat 'set BUILD_DURATION_STR=' + currentBuild.durationString + ' && python notify.py "%WECHAT_WEBHOOK%" failure'
            }
        }
    }
}