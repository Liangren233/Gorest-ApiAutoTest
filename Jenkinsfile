pipeline {
    agent any

    // 触发器:pollSCM 每5分钟轮询,有新提交才构建(省资源,持续集成);cron 每天 02:00 全量(健康巡检,防外部接口变更)
    triggers {
        pollSCM('H/5 * * * *')   // 轮询 SCM,有更新才触发(持续集成)
        cron('0 2 * * *')        // 每天 02:00 定时全量(健康巡检)
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