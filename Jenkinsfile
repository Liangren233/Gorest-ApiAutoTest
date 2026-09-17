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
                def dur = currentBuild.durationString ?: '见详情页'
                def baseUrl = env.BUILD_URL ?: ''
                def repUrl = baseUrl ? (baseUrl + 'allure/') : 'N/A'
                def detUrl = baseUrl ? (baseUrl + 'console') : 'N/A'
                // Windows bat 传参：给带空格的耗时加引号，URL加引号防截断
                bat "python notify.py \"%WECHAT_WEBHOOK%\" success \"${dur}\" \"${repUrl}\" \"${detUrl}\""
            }
        }
        failure {
            script {
                def dur = currentBuild.durationString ?: '见详情页'
                def baseUrl = env.BUILD_URL ?: ''
                def repUrl = baseUrl ? (baseUrl + 'allure/') : 'N/A'
                def detUrl = baseUrl ? (baseUrl + 'console') : 'N/A'
                bat "python notify.py \"%WECHAT_WEBHOOK%\" failure \"${dur}\" \"${repUrl}\" \"${detUrl}\""
            }
        }
    }
}