#!/bin/bash
# BLIMS RNA Pipeline Build and Deploy Script

set -e  # Exit on error

# Configuration
ENVIRONMENT=${1:-dev}
REGION=${AWS_REGION:-"us-east-1"}
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
STACK_NAME="blims-rna-pipeline-${ENVIRONMENT}"
JOB_ROLE_ARN=$(aws cloudformation describe-stacks --stack-name "blims-${ENVIRONMENT}" --query "Stacks[0].Outputs[?OutputKey=='BatchJobRoleArn'].OutputValue" --output text --region ${REGION})

# Banner
echo "======================================================"
echo "  BLIMS RNA-Seq Pipeline Build & Deploy"
echo "======================================================"
echo "Environment: ${ENVIRONMENT}"
echo "Region:      ${REGION}"
echo "Account ID:  ${ACCOUNT_ID}"
echo "Stack Name:  ${STACK_NAME}"
echo "------------------------------------------------------"

# Check for AWS CLI
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed or not in PATH"
    echo "Please install the AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in PATH"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check AWS authentication
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "Error: Not authenticated with AWS."
    echo "Please run 'aws configure' or set up your AWS credentials."
    exit 1
fi

# Function to build and push a Docker image
build_and_push_image() {
    local module=$1
    local tag="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/blims-rna-pipeline:${module}-latest"
    
    echo "Building Docker image for ${module}..."
    # Standard docker build - simpler approach for cross-platform
    DOCKER_BUILDKIT=1 docker build -t ${tag} ./aws/rna_pipeline_dockerfiles/${module}/
    
    echo "Checking if ECR repository exists..."
    if ! aws ecr describe-repositories --repository-names "blims-rna-pipeline" --region ${REGION} > /dev/null 2>&1; then
        echo "Creating ECR repository..."
        aws ecr create-repository --repository-name "blims-rna-pipeline" --region ${REGION}
    fi
    
    echo "Authenticating with ECR..."
    aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
    
    echo "Pushing image to ECR..."
    docker push ${tag}
    
    echo "Image ${tag} pushed successfully"
}

# Deploy CloudFormation stack
deploy_cfn_stack() {
    echo "Deploying CloudFormation stack for RNA pipeline job definitions..."
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name ${STACK_NAME} --region ${REGION} > /dev/null 2>&1; then
        # Update the stack
        aws cloudformation update-stack \
            --stack-name ${STACK_NAME} \
            --template-body file://$(pwd)/aws/rna_pipeline_definitions.yaml \
            --parameters \
                ParameterKey=Environment,ParameterValue=${ENVIRONMENT} \
                ParameterKey=JobRoleArn,ParameterValue=${JOB_ROLE_ARN} \
            --capabilities CAPABILITY_IAM \
            --region ${REGION}
            
        echo "Waiting for stack update to complete..."
        aws cloudformation wait stack-update-complete --stack-name ${STACK_NAME} --region ${REGION}
    else
        # Create the stack
        aws cloudformation create-stack \
            --stack-name ${STACK_NAME} \
            --template-body file://$(pwd)/aws/rna_pipeline_definitions.yaml \
            --parameters \
                ParameterKey=Environment,ParameterValue=${ENVIRONMENT} \
                ParameterKey=JobRoleArn,ParameterValue=${JOB_ROLE_ARN} \
            --capabilities CAPABILITY_IAM \
            --region ${REGION}
            
        echo "Waiting for stack creation to complete..."
        aws cloudformation wait stack-create-complete --stack-name ${STACK_NAME} --region ${REGION}
    fi
    
    echo "CloudFormation stack deployment complete"
}

# Update config file with job definition ARNs
update_config() {
    echo "Updating config with RNA pipeline job definitions..."
    
    # Get ARNs
    local read_proc_arn=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='ReadProcessingJobDefinitionArn'].OutputValue" --output text --region ${REGION})
    local norm_arn=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='NormalizationJobDefinitionArn'].OutputValue" --output text --region ${REGION})
    local quant_arn=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='QuantificationJobDefinitionArn'].OutputValue" --output text --region ${REGION})
    local assembly_arn=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='AssemblyJobDefinitionArn'].OutputValue" --output text --region ${REGION})
    local annot_arn=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='AnnotationJobDefinitionArn'].OutputValue" --output text --region ${REGION})
    local db_arn=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='DatabaseUpdateJobDefinitionArn'].OutputValue" --output text --region ${REGION})
    
    # Update config file
    mkdir -p config
    CONFIG_FILE="config/aws_config.json"
    
    if [ -f "${CONFIG_FILE}" ]; then
        # Extract existing config
        local region=$(jq -r '.region' ${CONFIG_FILE})
        local env=$(jq -r '.environment' ${CONFIG_FILE})
        local bio_bucket=$(jq -r '.s3.bioinformatics_bucket' ${CONFIG_FILE})
        local app_bucket=$(jq -r '.s3.app_bucket' ${CONFIG_FILE})
        local samples_table=$(jq -r '.dynamodb.samples_table' ${CONFIG_FILE})
        local job_queue=$(jq -r '.batch.job_queue' ${CONFIG_FILE})
        local fastqc_job=$(jq -r '.batch.job_definitions.fastqc' ${CONFIG_FILE})
        local bwa_job=$(jq -r '.batch.job_definitions.bwa_mem' ${CONFIG_FILE})
        
        # Create updated config with RNA pipeline job definitions
        cat > ${CONFIG_FILE} << EOF
{
    "region": "${region}",
    "environment": "${env}",
    "s3": {
        "bioinformatics_bucket": "${bio_bucket}",
        "app_bucket": "${app_bucket}"
    },
    "dynamodb": {
        "samples_table": "${samples_table}"
    },
    "batch": {
        "job_queue": "${job_queue}",
        "job_definitions": {
            "fastqc": "${fastqc_job}",
            "bwa_mem": "${bwa_job}",
            "rna_read_processing": "${read_proc_arn}",
            "rna_normalization": "${norm_arn}",
            "rna_quantification": "${quant_arn}",
            "rna_assembly": "${assembly_arn}",
            "rna_annotation": "${annot_arn}",
            "rna_db_update": "${db_arn}"
        }
    }
}
EOF
    else
        echo "Error: config file ${CONFIG_FILE} does not exist. Please deploy the main stack first."
        exit 1
    fi
    
    echo "Config file updated with RNA pipeline job definitions"
}

# Main execution
main() {
    if [ "$2" == "--dry-run" ]; then
        echo "Running in dry-run mode, skipping actual deployment"
        exit 0
    fi
    
    echo "Do you want to build and push the Docker images? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        # Build all containers for RNA-Seq pipeline
        for container in read_processing normalization quantification assembly annotation db_update; do
            echo "Building ${container} container..."
            build_and_push_image "${container}" || { echo "Build failed for ${container}, but continuing with the rest of the script"; }
        done
        echo "Image build and push complete."
    fi
    
    echo "Do you want to deploy the CloudFormation stack with job definitions? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        deploy_cfn_stack
        update_config
        echo "Deployment complete."
    fi
    
    echo "======================================================"
    echo "  RNA-Seq Pipeline Deployment Complete!"
    echo "======================================================"
}

# Start the process
main $@