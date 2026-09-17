pipeline {
    agent any

    environment {
        GOREST_TOKEN = credentials('gorest-token')
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
                def msg = """✅ **接口自动化测试通过**
> 项目：${env.JOB_NAME}
> 构建：#${env.BUILD_NUMBER}
> 分支：${env.BRANCH_NAME}
> 详情：${env.BUILD_URL}"""
                wechatNotify(msg)
            }
        }
        failure {
            script {
                def msg = """❌ **接口自动化测试失败**
> 项目：${env.JOB_NAME}
> 构建：#${env.BUILD_NUMBER}
> 分支：${env.BRANCH_NAME}
> 详情：${env.BUILD_URL}allure/"""
                wechatNotify(msg)
            }
        }
    }
}

def wechatNotify(String content) {
    def webhook = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的企微机器人key'
    def escaped = content.replace('"', '\\"').replace('\n', '\\n')
    powershell """
\$body = '{"msgtype": "markdown", "markdown": {"content": "${escaped}"}}'
Invoke-RestMethod -Uri '${webhook}' -Method Post -ContentType 'application/json' -Body \$body
"""
}