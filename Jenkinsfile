pipeline {
    agent none

    parameters {
        choice(name: 'ACTION', choices: ['apply', 'delete'], description: 'Select whether to apply or delete resources')
        string(name: 'CLUSTER_NAME', defaultValue: 'pdf-gpt-cluster', description: 'EKS Cluster Name')
        string(name: 'AWS_REGION', defaultValue: 'us-east-1', description: 'AWS Region')
        string(name: 'NODE_LABEL', defaultValue: 'any', description: 'Select the node to use')
    }

    // environment {}
    
    stages {
        stage('Checkout') {
            agent { node { label "${params.NODE_LABEL}" } }
            steps {
                checkout scm
            }
        }
        
        stage('Verify AWS & Kubectl Access') {
            agent { node { label "${params.NODE_LABEL}" } }
            steps {
                sh '''
                    aws eks update-kubeconfig --name ${CLUSTER_NAME} --region ${AWS_REGION}
                    kubectl config current-context
                    kubectl get nodes
                '''
            }
        }
        
        stage('Run Bash Scripts') {
            agent { node { label "${params.NODE_LABEL}" } }
            when {
                expression { params.ACTION == 'apply' }
            }
            steps {
                sh '''
                    chmod +x ./k8s/*.sh
                    cd k8s
                    ./deploy-redis.sh
                    ./secret.sh
                '''
            }
        }
        
        stage('Apply K8s Resources') {
            agent { node { label "${params.NODE_LABEL}" } }
            when {
                expression { params.ACTION == 'apply' }
            }
            steps {
                sh '''
                    kubectl apply -f ./k8s/pvc-pv.yaml
                    kubectl apply -f ./k8s/deployment.yaml
                    kubectl apply -f ./k8s/service.yaml
                    kubectl apply -f ./k8s/hpa.yaml
                    kubectl apply -f ./k8s/nginx_ingress_rule.yaml
                    kubectl apply -f ./k8s/cronjob.yaml
                '''
            }
        }
        
        stage('Delete K8s Resources') {
            agent { node { label "${params.NODE_LABEL}" } }
            when {
                expression { params.ACTION == 'delete' }
            }
            steps {
                sh '''
                    kubectl delete -f ./k8s/cronjob.yaml --ignore-not-found
                    kubectl delete -f ./k8s/nginx_ingress_rule.yaml --ignore-not-found
                    kubectl delete -f ./k8s/hpa.yaml --ignore-not-found
                    kubectl delete -f ./k8s/service.yaml --ignore-not-found
                    kubectl delete -f ./k8s/deployment.yaml --ignore-not-found
                    kubectl delete -f ./k8s/pvc-pv.yaml --ignore-not-found
                '''
            }
        }
        
        stage('Verify Deployment') {
            agent { node { label "${params.NODE_LABEL}" } }
            when {
                expression { params.ACTION == 'apply' }
            }
            steps {
                sh '''
                    # Get namespace from deployment
                    NAMESPACE=$(kubectl get deployment -l app=pdf-gpt -o jsonpath='{.items[0].metadata.namespace}')
                    # Wait for pods to be ready
                    kubectl wait --for=condition=ready pod -l app=pdf-gpt -n ${NAMESPACE} --timeout=300s
                    # Display deployment status
                    kubectl get pods,svc,ingress -n ${NAMESPACE}
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
                body: """<p>Build Status: ${currentBuild.currentResult}</p>
                <p>Build URL: ${env.BUILD_URL}</p>
                <p>Build Number: ${env.BUILD_NUMBER}</p>
                <p>Action: ${params.ACTION}</p>
                <p>Cluster: ${params.CLUSTER_NAME}</p>
                <p>Region: ${params.AWS_REGION}</p>""",
                recipientProviders: [[$class: 'DevelopersRecipientProvider'], [$class: 'RequesterRecipientProvider']]
            )
        }
    }
}
