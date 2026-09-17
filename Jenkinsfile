pipeline {
    agent any

    environment {
        GOREST_TOKEN = credentials('gorest-token')
        // 企微机器人 Webhook 通过凭证注入（在 Jenkins 中创建类型为 Secret Text 的凭证，ID 设为 wechat-webhook）
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

/* ================= 通知方法封装 ================= */

// 企微通知（PowerShell 防转义/防乱码 + 异常捕获）
def sendWechat(String content) {
    def escaped = content.replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\n')
    powershell """
\$body = '{"msgtype": "markdown", "markdown": {"content": "${escaped}"}}'
try {
  Invoke-RestMethod -Uri '${env.WECHAT_WEBHOOK}' -Method Post -ContentType 'application/json' -Body \$body
  Write-Output "Wechat notify success"
} catch {
  Write-Output "Wechat notify failed: \$_"
}
"""
}