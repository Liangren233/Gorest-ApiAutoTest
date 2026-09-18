pipeline {
    agent any

    // 触发器:每5分钟轮询仓库,有新提交自动构建;每天 02:00 定时全量构建
    triggers {
        pollSCM('H/5 * * * *')   // 每5分钟轮询 SCM,有更新才触发
        cron('0 2 * * *')        // 每天 02:00 定时执行
    }

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
                bat 'pytest'
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
        always {
            script {
                bat 'set BUILD_DURATION=' + currentBuild.durationString + ' && echo duration injected'
            }
        }
    }
}