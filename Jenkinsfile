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
            def branch = env.BRANCH_NAME ?: "master"
            def duration = currentBuild.durationString ?: "N/A"
            def reportUrl = "${env.BUILD_URL}allure/"
            def msg = """✅ **接口自动化测试通过**
> 项目：${env.JOB_NAME}
> 构建：#${env.BUILD_NUMBER}
> 分支：${branch}
> 耗时：${duration}
> 报告：[点击查看 Allure](${reportUrl})
> 详情：${env.BUILD_URL}"""
            sendWechat(msg)
        }
    }
    failure {
        script {
            def branch = env.BRANCH_NAME ?: "master"
            def duration = currentBuild.durationString ?: "N/A"
            def reportUrl = "${env.BUILD_URL}allure/"
            def msg = """❌ **接口自动化测试失败**
> 项目：${env.JOB_NAME}
> 构建：#${env.BUILD_NUMBER}
> 分支：${branch}
> 耗时：${duration}
> 报告：[点击查看 Allure](${reportUrl})
> 详情：${env.BUILD_URL}console"""
            sendWechat(msg)
        }
    }
}

def sendWechat(String content) {
    writeFile file: 'notify_msg.txt', text: content, encoding: 'UTF-8'
    bat 'python notify.py "%WECHAT_WEBHOOK%" notify_msg.txt'
}