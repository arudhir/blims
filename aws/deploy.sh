#!/bin/bash
# BLIMS AWS deployment script

set -e  # Exit on error

# Configuration
STACK_NAME_PREFIX="blims"
ENVIRONMENT=${1:-dev}
STACK_NAME="${STACK_NAME_PREFIX}-${ENVIRONMENT}"
VPC_STACK_NAME="${STACK_NAME_PREFIX}-vpc-${ENVIRONMENT}"
REGION=${AWS_REGION:-"us-east-1"}  # Default to us-east-1 or use AWS_REGION env var

# Banner
echo "======================================================"
echo "  BLIMS AWS Infrastructure Deployment"
echo "======================================================"
echo "Environment: ${ENVIRONMENT}"
echo "Region:      ${REGION}"
echo "VPC Stack:   ${VPC_STACK_NAME}"
echo "Main Stack:  ${STACK_NAME}"
echo "------------------------------------------------------"

# Check for AWS CLI
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed or not in PATH"
    echo "Please install the AWS CLI: https://aws.amazon.com/cli/"
    exit 1
fi

# Check AWS authentication
echo "Checking AWS credentials..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "Error: Not authenticated with AWS."
    echo "Please run 'aws configure' or set up your AWS credentials."
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
echo "Using AWS Account: ${AWS_ACCOUNT_ID}"
echo

# Function to wait for stack completion
wait_for_stack() {
    local stack_name=$1
    echo "Waiting for stack ${stack_name} to complete..."
    
    aws cloudformation wait stack-${2:-create}-complete \
        --stack-name ${stack_name} \
        --region ${REGION}
        
    if [ $? -ne 0 ]; then
        echo "Error: Stack operation failed or timed out"
        echo "Check the AWS CloudFormation console for details"
        exit 1
    fi
    
    echo "Stack ${stack_name} completed successfully"
}

# Determine if this is a create or update
check_stack_exists() {
    local stack_name=$1
    if aws cloudformation describe-stacks --stack-name ${stack_name} --region ${REGION} > /dev/null 2>&1; then
        return 0  # Stack exists
    else
        return 1  # Stack doesn't exist
    fi
}

# Create or update VPC stack
deploy_vpc_stack() {
    if check_stack_exists ${VPC_STACK_NAME}; then
        echo "Updating VPC stack ${VPC_STACK_NAME}..."
        
        # Update the stack
        aws cloudformation update-stack \
            --stack-name ${VPC_STACK_NAME} \
            --template-body file://$(pwd)/aws/blims-vpc.yaml \
            --parameters ParameterKey=EnvironmentName,ParameterValue=${ENVIRONMENT} \
            --capabilities CAPABILITY_IAM \
            --region ${REGION} \
            --no-cli-pager
            
        # Wait for update to complete
        wait_for_stack ${VPC_STACK_NAME} "update"
    else
        echo "Creating VPC stack ${VPC_STACK_NAME}..."
        
        # Create the stack
        aws cloudformation create-stack \
            --stack-name ${VPC_STACK_NAME} \
            --template-body file://$(pwd)/aws/blims-vpc.yaml \
            --parameters ParameterKey=EnvironmentName,ParameterValue=${ENVIRONMENT} \
            --capabilities CAPABILITY_IAM \
            --region ${REGION} \
            --no-cli-pager
            
        # Wait for creation to complete
        wait_for_stack ${VPC_STACK_NAME}
    fi
    
    echo "VPC stack deployment complete."
}

# Create or update main stack
deploy_main_stack() {
    local bucket_name="${STACK_NAME_PREFIX}-${ENVIRONMENT}-${AWS_ACCOUNT_ID}"
    local dynamodb_table_name="${STACK_NAME_PREFIX}-samples-${ENVIRONMENT}"
    local batch_compute_env="${STACK_NAME_PREFIX}-compute-${ENVIRONMENT}"
    local batch_job_queue="${STACK_NAME_PREFIX}-queue-${ENVIRONMENT}"

    if check_stack_exists ${STACK_NAME}; then
        echo "Updating main stack ${STACK_NAME}..."
        
        # Update the stack
        aws cloudformation update-stack \
            --stack-name ${STACK_NAME} \
            --template-body file://$(pwd)/aws/cloudformation.yaml \
            --parameters \
                ParameterKey=Environment,ParameterValue=${ENVIRONMENT} \
                ParameterKey=BucketNamePrefix,ParameterValue=${bucket_name} \
                ParameterKey=DynamoDBTableName,ParameterValue=${dynamodb_table_name} \
                ParameterKey=BatchComputeEnvironmentName,ParameterValue=${batch_compute_env} \
                ParameterKey=BatchJobQueueName,ParameterValue=${batch_job_queue} \
            --capabilities CAPABILITY_IAM \
            --region ${REGION} \
            --no-cli-pager
            
        # Wait for update to complete
        wait_for_stack ${STACK_NAME} "update"
    else
        echo "Creating main stack ${STACK_NAME}..."
        
        # Create the stack
        aws cloudformation create-stack \
            --stack-name ${STACK_NAME} \
            --template-body file://$(pwd)/aws/cloudformation.yaml \
            --parameters \
                ParameterKey=Environment,ParameterValue=${ENVIRONMENT} \
                ParameterKey=BucketNamePrefix,ParameterValue=${bucket_name} \
                ParameterKey=DynamoDBTableName,ParameterValue=${dynamodb_table_name} \
                ParameterKey=BatchComputeEnvironmentName,ParameterValue=${batch_compute_env} \
                ParameterKey=BatchJobQueueName,ParameterValue=${batch_job_queue} \
            --capabilities CAPABILITY_IAM \
            --region ${REGION} \
            --no-cli-pager
            
        # Wait for creation to complete
        wait_for_stack ${STACK_NAME}
    fi
    
    echo "Main stack deployment complete."
}

# Generate configuration file for the application
generate_config() {
    echo "Generating AWS configuration..."
    
    # Get outputs from CloudFormation stacks
    local bioinformatics_bucket=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='BioinformaticsBucketName'].OutputValue" --output text --region ${REGION})
    local app_bucket=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='AppBucketName'].OutputValue" --output text --region ${REGION})
    local samples_table=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='SamplesTableName'].OutputValue" --output text --region ${REGION})
    local job_queue=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='BatchJobQueueName'].OutputValue" --output text --region ${REGION})
    local fastqc_job=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='FastQCJobDefinitionArn'].OutputValue" --output text --region ${REGION})
    local bwa_job=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='BwaMemJobDefinitionArn'].OutputValue" --output text --region ${REGION})
    
    # Create config file
    mkdir -p config
    cat > config/aws_config.json << EOF
{
    "region": "${REGION}",
    "environment": "${ENVIRONMENT}",
    "s3": {
        "bioinformatics_bucket": "${bioinformatics_bucket}",
        "app_bucket": "${app_bucket}"
    },
    "dynamodb": {
        "samples_table": "${samples_table}"
    },
    "batch": {
        "job_queue": "${job_queue}",
        "job_definitions": {
            "fastqc": "${fastqc_job}",
            "bwa_mem": "${bwa_job}"
        }
    }
}
EOF

    echo "Configuration file generated at config/aws_config.json"
}

# Run a dry run validation
validate_templates() {
    echo "Validating CloudFormation templates..."
    
    # Validate VPC template
    echo "Validating VPC template..."
    aws cloudformation validate-template \
        --template-body file://$(pwd)/aws/blims-vpc.yaml \
        --region ${REGION} > /dev/null
        
    echo "VPC template is valid."
    
    # Validate main template
    echo "Validating main template..."
    aws cloudformation validate-template \
        --template-body file://$(pwd)/aws/cloudformation.yaml \
        --region ${REGION} > /dev/null
        
    echo "Main template is valid."
}

# Main deployment process
main() {
    validate_templates
    
    echo "Do you want to proceed with deployment? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        # Deploy VPC stack
        deploy_vpc_stack
        
        # Give a little time for outputs to be available
        sleep 5
        
        # Deploy main stack
        deploy_main_stack
        
        # Generate config
        generate_config
        
        echo "======================================================"
        echo "  BLIMS AWS Infrastructure Deployment Complete!"
        echo "======================================================"
    else
        echo "Deployment canceled."
    fi
}

# Dry run mode - just validate the templates
if [ "$2" == "--dry-run" ]; then
    echo "Running in dry-run mode (validation only)..."
    validate_templates
    exit 0
fi

# Start the deployment
main