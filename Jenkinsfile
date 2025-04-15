pipeline {
    agent {
        node {
            label 'eks-node'
        }
    }

    parameters {
        choice(name: 'ACTION', choices: ['apply', 'delete'], description: 'Select whether to apply or delete resources')
        string(name: 'CLUSTER_NAME', defaultValue: 'pdf-gpt-cluster', description: 'EKS Cluster Name')
        string(name: 'AWS_REGION', defaultValue: 'us-east-2', description: 'AWS Region')
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
        
        stage('Prepare Secrets') {
            when {
                expression { params.ACTION == 'apply' }
            }
            steps {
                sh '''
                    # Ensure that OPENAI_API_KEY is defined; exit if not
                    if [ -z "${OPENAI_API_KEY:-}" ]; then
                      echo "Error: OPENAI_API_KEY is not set."
                      exit 1
                    elif [ -z "${INGRESS_HOST}" ]; then
                      echo "Error: INGRESS_HOST is not set."
                      exit 1
                    fi

                    # Make k8s scripts executable
                    chmod +x ./k8s/*.sh

                    # Generate secrets.yaml from the template by converting the API key to Base64
                    echo "Generating secrets.yaml from secrets.yaml.template..."
                    export OPENAI_API_KEY_B64=$(echo -n "${OPENAI_API_KEY}" | base64)
                    envsubst < ./k8s/secrets.yaml.template > ./k8s/secrets.yaml
                    echo "Generated secrets.yaml:"
                    cat ./k8s/secrets.yaml
                '''
            }
        }
        
        stage('Apply Resources') {
            when {
                expression { params.ACTION == 'apply' }
            }
             steps {
                sh '''
                    ./k8s/manage-redis.sh create
                    kubectl apply -f ./k8s/secrets.yaml
                    kubectl apply -f ./k8s/pvc-pv.yaml
                    kubectl apply -f ./k8s/deployment.yaml
                    kubectl apply -f ./k8s/service.yaml
                    kubectl apply -f ./k8s/hpa.yaml
                    envsubst < ./k8s/nginx_ingress_rule.yaml | kubectl apply -f -
                    kubectl apply -f ./k8s/cronjob.yaml
                '''
            }
        }
        
        stage('Delete Resources') {
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
                    kubectl delete -f ./k8s/secrets.yaml --ignore-not-found
                    ./k8s/manage-redis.sh delete
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
