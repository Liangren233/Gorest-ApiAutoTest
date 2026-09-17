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
                def branch = env.BRANCH_NAME != null ? env.BRANCH_NAME : 'master'
                def duration = currentBuild.durationString != null ? currentBuild.durationString : 'N/A'
                def reportUrl = env.BUILD_URL + 'allure/'
                def msg = '✅ 接口自动化测试通过\n> 项目：' + env.JOB_NAME + '\n> 构建：#' + env.BUILD_NUMBER + '\n> 分支：' + branch + '\n> 耗时：' + duration + '\n> 报告：' + reportUrl + '\n> 详情：' + env.BUILD_URL
                sendWechat(msg)
            }
        }
        failure {
            script {
                def branch = env.BRANCH_NAME != null ? env.BRANCH_NAME : 'master'
                def duration = currentBuild.durationString != null ? currentBuild.durationString : 'N/A'
                def reportUrl = env.BUILD_URL + 'allure/'
                def msg = '❌ 接口自动化测试失败\n> 项目：' + env.JOB_NAME + '\n> 构建：#' + env.BUILD_NUMBER + '\n> 分支：' + branch + '\n> 耗时：' + duration + '\n> 报告：' + reportUrl + '\n> 详情：' + env.BUILD_URL + 'console'
                sendWechat(msg)
            }
        }
    }
}

def sendWechat(String content) {
    writeFile file: 'notify_msg.txt', text: content, encoding: 'UTF-8'
    bat 'python notify.py "%WECHAT_WEBHOOK%" notify_msg.txt'
}