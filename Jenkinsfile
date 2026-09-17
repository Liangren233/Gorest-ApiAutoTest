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
                def reportUrl = "${env.BUILD_URL}allure/"
                def msg = """✅ **接口自动化测试通过**
> 项目：${env.JOB_NAME}
> 构建：#${env.BUILD_NUMBER}
> 分支：${env.BRANCH_NAME}
> 耗时：${currentBuild.durationString}
> 报告：[点击查看 Allure](${reportUrl})
> 详情：${env.BUILD_URL}"""
                sendWechat(msg)
            }
        }
        failure {
            script {
                def reportUrl = "${env.BUILD_URL}allure/"
                def msg = """❌ **接口自动化测试失败**
> 项目：${env.JOB_NAME}
> 构建：#${env.BUILD_NUMBER}
> 分支：${env.BRANCH_NAME}
> 耗时：${currentBuild.durationString}
> 报告：[点击查看 Allure](${reportUrl})
> 详情：${env.BUILD_URL}console"""
                sendWechat(msg)
            }
        }
    }
}

def sendWechat(String content) {
    def escaped = content.replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\n')
    withEnv(["WEBHOOK=${env.WECHAT_WEBHOOK}", "MSG=${escaped}"]) {
        powershell '''
$body = "{`"msgtype`": `"markdown`", `"markdown`": {`"content`": `"$env:MSG`"}}"
try {
    Invoke-RestMethod -Uri $env:WEBHOOK -Method Post -ContentType "application/json" -Body $body
    Write-Output "Wechat notify success"
} catch {
    Write-Output "Wechat notify failed: $_"
}
'''
    }
}