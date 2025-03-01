#!/bin/bash
# BLIMS AWS Resource Status Check Script

set -e  # Exit on error

# Configuration
STACK_NAME_PREFIX="blims"
ENVIRONMENT=${1:-dev}
STACK_NAME="${STACK_NAME_PREFIX}-${ENVIRONMENT}"
VPC_STACK_NAME="${STACK_NAME_PREFIX}-vpc-${ENVIRONMENT}"
REGION=${AWS_REGION:-"us-east-1"}  # Default to us-east-1 or use AWS_REGION env var

# Banner
echo "======================================================"
echo "  BLIMS AWS Infrastructure Status Check"
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

# Function to check stack status
check_stack_status() {
    local stack_name=$1
    echo "Checking ${stack_name} status..."
    
    if aws cloudformation describe-stacks --stack-name ${stack_name} --region ${REGION} > /dev/null 2>&1; then
        local status=$(aws cloudformation describe-stacks --stack-name ${stack_name} --query "Stacks[0].StackStatus" --output text --region ${REGION})
        echo "  Status: ${status}"
        
        # Get creation and last updated time
        local creation_time=$(aws cloudformation describe-stacks --stack-name ${stack_name} --query "Stacks[0].CreationTime" --output text --region ${REGION})
        echo "  Created: ${creation_time}"
        
        local last_updated=$(aws cloudformation describe-stacks --stack-name ${stack_name} --query "Stacks[0].LastUpdatedTime" --output text --region ${REGION} 2>/dev/null)
        if [ ! -z "$last_updated" ] && [ "$last_updated" != "None" ]; then
            echo "  Last Updated: ${last_updated}"
        fi
        
        return 0  # Stack exists
    else
        echo "  Status: DOES NOT EXIST"
        return 1  # Stack doesn't exist
    fi
}

# Function to check VPC resources
check_vpc_resources() {
    if check_stack_status ${VPC_STACK_NAME}; then
        echo "  VPC resources:"
        
        # Get VPC ID
        local vpc_id=$(aws cloudformation describe-stack-resources --stack-name ${VPC_STACK_NAME} --logical-resource-id VPC --query "StackResources[0].PhysicalResourceId" --output text --region ${REGION} 2>/dev/null)
        if [ ! -z "$vpc_id" ] && [ "$vpc_id" != "None" ]; then
            echo "    VPC ID: ${vpc_id}"
            
            # Count subnets in the VPC
            local subnet_count=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=${vpc_id}" --query "length(Subnets)" --output text --region ${REGION})
            echo "    Subnets: ${subnet_count}"
            
            # Security groups
            local sg_count=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=${vpc_id}" --query "length(SecurityGroups)" --output text --region ${REGION})
            echo "    Security Groups: ${sg_count}"
        else
            echo "    VPC details not available"
        fi
    fi
}

# Function to check S3 buckets
check_s3_buckets() {
    if check_stack_status ${STACK_NAME}; then
        echo "  S3 Buckets:"
        
        # Get bucket names from stack outputs
        local bioinformatics_bucket=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='BioinformaticsBucketName'].OutputValue" --output text --region ${REGION} 2>/dev/null)
        local app_bucket=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='AppBucketName'].OutputValue" --output text --region ${REGION} 2>/dev/null)
        
        if [ ! -z "$bioinformatics_bucket" ] && [ "$bioinformatics_bucket" != "None" ]; then
            echo "    Bioinformatics Bucket: ${bioinformatics_bucket}"
            # Get object count
            local object_count=$(aws s3api list-objects-v2 --bucket ${bioinformatics_bucket} --query "length(Contents[])" --output text 2>/dev/null || echo "0")
            echo "      Objects: ${object_count}"
        fi
        
        if [ ! -z "$app_bucket" ] && [ "$app_bucket" != "None" ]; then
            echo "    App Bucket: ${app_bucket}"
            # Get object count
            local object_count=$(aws s3api list-objects-v2 --bucket ${app_bucket} --query "length(Contents[])" --output text 2>/dev/null || echo "0")
            echo "      Objects: ${object_count}"
        fi
    fi
}

# Function to check DynamoDB tables
check_dynamodb() {
    if check_stack_status ${STACK_NAME}; then
        echo "  DynamoDB:"
        
        # Get table name
        local samples_table=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='SamplesTableName'].OutputValue" --output text --region ${REGION} 2>/dev/null)
        
        if [ ! -z "$samples_table" ] && [ "$samples_table" != "None" ]; then
            echo "    Samples Table: ${samples_table}"
            
            # Get table status
            local table_status=$(aws dynamodb describe-table --table-name ${samples_table} --query "Table.TableStatus" --output text --region ${REGION} 2>/dev/null || echo "NOT FOUND")
            echo "      Status: ${table_status}"
            
            # Get item count
            if [ "$table_status" == "ACTIVE" ]; then
                local item_count=$(aws dynamodb describe-table --table-name ${samples_table} --query "Table.ItemCount" --output text --region ${REGION})
                echo "      Items: ${item_count}"
            fi
        fi
    fi
}

# Function to check AWS Batch resources
check_batch_resources() {
    if check_stack_status ${STACK_NAME}; then
        echo "  AWS Batch:"
        
        # Get compute environment and job queue
        local compute_env=$(aws cloudformation describe-stack-resources --stack-name ${STACK_NAME} --logical-resource-id BatchComputeEnvironment --query "StackResources[0].PhysicalResourceId" --output text --region ${REGION} 2>/dev/null)
        local job_queue=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='BatchJobQueueName'].OutputValue" --output text --region ${REGION} 2>/dev/null)
        
        if [ ! -z "$compute_env" ] && [ "$compute_env" != "None" ]; then
            echo "    Compute Environment: ${compute_env}"
            
            # Get compute environment status
            local ce_status=$(aws batch describe-compute-environments --compute-environments ${compute_env} --query "computeEnvironments[0].status" --output text --region ${REGION} 2>/dev/null || echo "NOT FOUND")
            local ce_state=$(aws batch describe-compute-environments --compute-environments ${compute_env} --query "computeEnvironments[0].state" --output text --region ${REGION} 2>/dev/null || echo "UNKNOWN")
            echo "      Status: ${ce_status} (${ce_state})"
        fi
        
        if [ ! -z "$job_queue" ] && [ "$job_queue" != "None" ]; then
            echo "    Job Queue: ${job_queue}"
            
            # Get job queue status
            local jq_status=$(aws batch describe-job-queues --job-queues ${job_queue} --query "jobQueues[0].status" --output text --region ${REGION} 2>/dev/null || echo "NOT FOUND")
            local jq_state=$(aws batch describe-job-queues --job-queues ${job_queue} --query "jobQueues[0].state" --output text --region ${REGION} 2>/dev/null || echo "UNKNOWN")
            echo "      Status: ${jq_status} (${jq_state})"
            
            # List active jobs
            local active_jobs=$(aws batch list-jobs --job-queue ${job_queue} --job-status "RUNNING" --region ${REGION} 2>/dev/null)
            local active_count=$(echo $active_jobs | jq -r '.jobSummaryList | length' 2>/dev/null || echo "0")
            echo "      Running Jobs: ${active_count}"
        fi
        
        # Check job definitions
        echo "    Job Definitions:"
        local fastqc_job=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='FastQCJobDefinitionArn'].OutputValue" --output text --region ${REGION} 2>/dev/null)
        local bwa_job=$(aws cloudformation describe-stacks --stack-name ${STACK_NAME} --query "Stacks[0].Outputs[?OutputKey=='BwaMemJobDefinitionArn'].OutputValue" --output text --region ${REGION} 2>/dev/null)
        
        if [ ! -z "$fastqc_job" ] && [ "$fastqc_job" != "None" ]; then
            echo "      FastQC: ${fastqc_job##*/}"
        fi
        
        if [ ! -z "$bwa_job" ] && [ "$bwa_job" != "None" ]; then
            echo "      BWA-MEM: ${bwa_job##*/}"
        fi
    fi
}

# Function to estimate costs
estimate_costs() {
    echo "  Cost Estimates (Monthly):"
    echo "    Note: These are rough estimates based on AWS pricing. Actual costs may vary."
    
    # S3 Storage - assuming 100GB average
    echo "    S3 Storage: ~$2.30 (100GB Standard Storage)"
    
    # DynamoDB
    echo "    DynamoDB: ~$0.25 (On-demand capacity mode with low usage)"
    
    # Batch (EC2) - assuming 10 hours of m5.large usage
    echo "    AWS Batch: ~$0.96 (10 hours of m5.large @ $0.096/hour)"
    
    # Basic infrastructure (VPC, etc.)
    echo "    Infrastructure: ~$0.00 (AWS doesn't charge for VPC)"
    
    # Total
    echo "    Estimated Total: ~$3.51/month"
    echo "    (This assumes light usage. Costs scale with usage.)"
}

# Main function
main() {
    echo "Checking AWS infrastructure status for BLIMS..."
    echo
    
    # Check stack statuses
    echo "Stack Status:"
    check_stack_status ${VPC_STACK_NAME}
    echo
    check_stack_status ${STACK_NAME}
    echo
    
    # Check VPC resources
    echo "VPC Resources:"
    check_vpc_resources
    echo
    
    # Check S3 buckets
    echo "S3 Buckets:"
    check_s3_buckets
    echo
    
    # Check DynamoDB
    echo "DynamoDB:"
    check_dynamodb
    echo
    
    # Check Batch resources
    echo "AWS Batch:"
    check_batch_resources
    echo
    
    # Estimated costs
    echo "Cost Estimates:"
    estimate_costs
    echo
    
    echo "======================================================"
    echo "  Status Check Complete"
    echo "======================================================"
}

# Start the process
main