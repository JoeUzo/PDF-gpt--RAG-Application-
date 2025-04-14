pipeline {
    agent {
        node {
            label 'eks-node'
        }
    }

    parameters {
        choice(name: 'ACTION', choices: ['apply', 'delete'], description: 'Select whether to apply or delete resources')
        string(name: 'CLUSTER_NAME', defaultValue: 'pdf-gpt-cluster', description: 'EKS Cluster Name')
        string(name: 'AWS_REGION', defaultValue: 'us-east-1', description: 'AWS Region')
    }

    // environment {}
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Verify AWS & Kubectl Access') {
            steps {
                sh '''
                    aws eks update-kubeconfig --name ${CLUSTER_NAME} --region ${AWS_REGION}
                    kubectl config current-context
                    kubectl get nodes
                '''
            }
        }
        
        stage('Run Bash Scripts') {
            when {
                expression { params.ACTION == 'apply' }
            }
            steps {
                sh '''
                    chmod +x ./k8s/*.sh
                    cd k8s
                    ./deploy-redis.sh
                '''
                withCredentials([file(credentialsId: 'secrets_sh', variable: 'SECRET_SCRIPT')]) {
                    sh '''
                        chmod +x ${SECRET_SCRIPT}
                        ${SECRET_SCRIPT}
                    '''
                }
            }
        }
        
        stage('Apply K8s Resources') {
            when {
                expression { params.ACTION == 'apply' }
            }
            steps {
                sh '''
                    kubectl apply -f ./k8s/pvc-pv.yaml
                    kubectl apply -f ./k8s/deployment.yaml
                    kubectl apply -f ./k8s/service.yaml
                    kubectl apply -f ./k8s/hpa.yaml
                    envsubst < ./k8s/nginx_ingress_rule.yaml | kubectl apply -f -
                    kubectl apply -f ./k8s/cronjob.yaml
                '''
            }
        }
        
        stage('Delete K8s Resources') {
            when {
                expression { params.ACTION == 'delete' }
            }
            steps {
                sh '''
                    kubectl delete -f ./k8s/cronjob.yaml --ignore-not-found
                    envsubst < ./k8s/nginx_ingress_rule.yaml | kubectl delete -f - --ignore-not-found
                    kubectl delete -f ./k8s/hpa.yaml --ignore-not-found
                    kubectl delete -f ./k8s/service.yaml --ignore-not-found
                    kubectl delete -f ./k8s/deployment.yaml --ignore-not-found
                    kubectl delete -f ./k8s/pvc-pv.yaml --ignore-not-found
                    kubectl delete secret pdf-gpt-secrets -n app --ignore-not-found
                    helm uninstall my-redis -n redis
                    helm repo remove bitnami
                    kubectl delete namespace redis --ignore-not-found
                '''
            }
        }
    }
    
    post {
        success {
            slackSend(
                color: 'good',
                message: "Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' completed successfully (${env.BUILD_URL})"
            )
        }
        failure {
            slackSend(
                color: 'danger',
                message: "Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]' failed (${env.BUILD_URL})"
            )
        }
        always {
            // Clean workspace
            cleanWs()
            
            // Archive artifacts
            archiveArtifacts artifacts: '**/logs/**/*.log', allowEmptyArchive: true
            
            // Send email notification
            emailext (
                subject: "${env.JOB_NAME} - Build # ${env.BUILD_NUMBER} - ${currentBuild.currentResult}",
                body: """Build Status: ${currentBuild.currentResult}
                Build URL: ${env.BUILD_URL}
                Build Number: ${env.BUILD_NUMBER}
                Action: ${params.ACTION}
                Cluster: ${params.CLUSTER_NAME}
                Region: ${params.AWS_REGION}""",
                recipientProviders: [[$class: 'DevelopersRecipientProvider'], [$class: 'RequesterRecipientProvider']]
            )
        }
    }
}
