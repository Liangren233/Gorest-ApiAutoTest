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
                def reportUrl = env.BUILD_URL != null ? env.BUILD_URL + 'allure/' : 'N/A'
                def detailUrl = env.BUILD_URL != null ? env.BUILD_URL + 'console' : 'N/A'
                def duration = currentBuild.durationString != null ? currentBuild.durationString : '见详情页'
                bat "python notify.py \"%WECHAT_WEBHOOK%\" success \"" + duration + "\" \"" + reportUrl + "\" \"" + detailUrl + "\""
            }
        }
        failure {
            script {
                def reportUrl = env.BUILD_URL != null ? env.BUILD_URL + 'allure/' : 'N/A'
                def detailUrl = env.BUILD_URL != null ? env.BUILD_URL + 'console' : 'N/A'
                def duration = currentBuild.durationString != null ? currentBuild.durationString : '见详情页'
                bat "python notify.py \"%WECHAT_WEBHOOK%\" failure \"" + duration + "\" \"" + reportUrl + "\" \"" + detailUrl + "\""
            }
        }
    }
}