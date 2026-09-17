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
                def jenkinsUrl = env.JENKINS_URL ?: 'http://localhost:8080/'
                def jobName = env.JOB_NAME ?: 'api-auto-test'
                def buildNum = env.BUILD_NUMBER ?: '1'
                // 手动拼接 BUILD_URL
                def baseUrl = jenkinsUrl + 'job/' + jobName + '/' + buildNum + '/'
                def repUrl = baseUrl + 'allure/'
                def detUrl = baseUrl + 'console'
                bat "python notify.py \"%WECHAT_WEBHOOK%\" success \"${dur}\" \"${repUrl}\" \"${detUrl}\""
            }
        }
        failure {
            script {
                def dur = currentBuild.durationString ?: '见详情页'
                def jenkinsUrl = env.JENKINS_URL ?: 'http://localhost:8080/'
                def jobName = env.JOB_NAME ?: 'api-auto-test'
                def buildNum = env.BUILD_NUMBER ?: '1'
                def baseUrl = jenkinsUrl + 'job/' + jobName + '/' + buildNum + '/'
                def repUrl = baseUrl + 'allure/'
                def detUrl = baseUrl + 'console'
                bat "python notify.py \"%WECHAT_WEBHOOK%\" failure \"${dur}\" \"${repUrl}\" \"${detUrl}\""
            }
        }
    }
}