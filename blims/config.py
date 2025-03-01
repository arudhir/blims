"""Configuration management for BLIMS."""

import os
import json
from typing import Any, Dict, Optional

# Default AWS region
DEFAULT_REGION = "us-east-1"

# AWS configuration
AWS_CONFIG_FILE = os.environ.get("BLIMS_CONFIG", "config/aws_config.json")


def get_aws_config() -> Dict[str, Any]:
    """Get AWS configuration for BLIMS.
    
    Returns:
        Configuration dictionary
    """
    # Default configuration
    default_config = {
        "region": DEFAULT_REGION,
        "environment": "dev",
        "s3": {
            "bioinformatics_bucket": "blims-bioinformatics-dev",
            "app_bucket": "blims-app-dev"
        },
        "dynamodb": {
            "samples_table": "blims-samples-dev"
        },
        "batch": {
            "job_queue": "blims-job-queue-dev",
            "job_definitions": {
                "fastqc": "blims-fastqc-dev",
                "bwa_mem": "blims-bwa-mem-dev"
            }
        }
    }
    
    # Try to load configuration file
    try:
        if os.path.exists(AWS_CONFIG_FILE):
            with open(AWS_CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load AWS configuration from {AWS_CONFIG_FILE}: {str(e)}")
        print("Using default configuration instead.")
        
    return default_config


def get_s3_bucket(bucket_type: str = "bioinformatics") -> str:
    """Get the S3 bucket name for BLIMS.
    
    Args:
        bucket_type: Type of bucket (bioinformatics or app)
        
    Returns:
        S3 bucket name
    """
    config = get_aws_config()
    return config["s3"].get(f"{bucket_type}_bucket", f"blims-{bucket_type}-{config['environment']}")


def get_dynamodb_table() -> str:
    """Get the DynamoDB table name for BLIMS.
    
    Returns:
        DynamoDB table name
    """
    config = get_aws_config()
    return config["dynamodb"].get("samples_table", f"blims-samples-{config['environment']}")


def get_batch_job_queue() -> str:
    """Get the AWS Batch job queue name for BLIMS.
    
    Returns:
        AWS Batch job queue name
    """
    config = get_aws_config()
    return config["batch"].get("job_queue", f"blims-job-queue-{config['environment']}")


def get_batch_job_definition(job_type: str) -> str:
    """Get an AWS Batch job definition for BLIMS.
    
    Args:
        job_type: Type of job (fastqc, bwa_mem, etc.)
        
    Returns:
        AWS Batch job definition name or ARN
    """
    config = get_aws_config()
    return config["batch"].get("job_definitions", {}).get(
        job_type, 
        f"blims-{job_type}-{config['environment']}"
    )


def get_aws_region() -> str:
    """Get the AWS region for BLIMS.
    
    Returns:
        AWS region
    """
    config = get_aws_config()
    return config.get("region", DEFAULT_REGION)