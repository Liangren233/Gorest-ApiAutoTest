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
    // 1. 将业务文本转为 UTF-8 字节流并 Base64 编码，彻底绕过 PowerShell 的引号/换行/特殊字符转义地狱
    def bytes = content.getBytes("UTF-8")
    def base64 = bytes.encodeBase64().toString()

    withEnv(["MSG_B64=${base64}"]) {
        powershell -ExecutionPolicy Bypass -Command {
            param()
            # 强制输出和请求均为 UTF-8
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
            $body = @{msgtype="markdown"; markdown=@{content=[System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:MSG_B64))}} | ConvertTo-Json -Depth 3
            try {
                Invoke-RestMethod -Uri $env:WECHAT_WEBHOOK -Method Post -ContentType "application/json; charset=utf-8" -Body $body
                Write-Output "Wechat notify success"
            } catch {
                Write-Output "Wechat notify failed: $_"
            }
        }
    }
}