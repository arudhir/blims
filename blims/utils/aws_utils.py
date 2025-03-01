"""AWS utility functions for BLIMS.

This module provides functionality for interacting with AWS services, including:
- S3 for file storage (sequencing data, analysis results)
- DynamoDB for database operations
- Batch for queuing and running bioinformatics analysis
"""

import os
import logging
import json
import uuid
import boto3
from botocore.exceptions import ClientError
from typing import Any, Dict, List, Optional, Union, BinaryIO, Tuple

from blims.config import get_aws_region, get_s3_bucket, get_dynamodb_table, get_batch_job_queue

# Set up logging
logger = logging.getLogger(__name__)

# Get AWS region from config
DEFAULT_REGION = get_aws_region()

class AWSManager:
    """Manager for AWS services used by BLIMS."""
    
    def __init__(self, region: str = DEFAULT_REGION):
        """Initialize the AWS Manager.
        
        Args:
            region: AWS region to use
        """
        self.region = region
        self.s3_client = None
        self.dynamodb_client = None
        self.dynamodb_resource = None
        self.batch_client = None
        
        # Initialize clients
        self.initialize_clients()
    
    def initialize_clients(self):
        """Initialize AWS service clients."""
        try:
            # S3 client for read/sequence data storage
            self.s3_client = boto3.client('s3', region_name=self.region)
            
            # DynamoDB for sample metadata and relationships
            self.dynamodb_client = boto3.client('dynamodb', region_name=self.region)
            self.dynamodb_resource = boto3.resource('dynamodb', region_name=self.region)
            
            # Batch for running bioinformatics analyses
            self.batch_client = boto3.client('batch', region_name=self.region)
            
            logger.info("AWS clients initialized successfully")
        except ClientError as e:
            logger.error(f"Failed to initialize AWS clients: {str(e)}")
            raise

    # S3 Operations for sequence data and analysis results
    
    def create_bucket(self, bucket_name: str) -> bool:
        """Create an S3 bucket for BLIMS data.
        
        Args:
            bucket_name: Name of the bucket to create
            
        Returns:
            True if bucket was created, False otherwise
        """
        try:
            self.s3_client.create_bucket(Bucket=bucket_name)
            logger.info(f"Created S3 bucket: {bucket_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to create bucket {bucket_name}: {str(e)}")
            return False
    
    def upload_file(self, file_path: str, bucket: str, object_name: Optional[str] = None,
                  metadata: Optional[Dict[str, str]] = None) -> bool:
        """Upload a file to an S3 bucket.
        
        Args:
            file_path: Path to the file to upload
            bucket: Bucket to upload to
            object_name: S3 object name (defaults to file_path basename)
            metadata: Optional metadata for the file
            
        Returns:
            True if file was uploaded, False otherwise
        """
        # If object_name not specified, use file_path basename
        if object_name is None:
            object_name = os.path.basename(file_path)
            
        # Add metadata if provided
        extra_args = {}
        if metadata:
            extra_args['Metadata'] = metadata
        
        try:
            self.s3_client.upload_file(
                file_path, 
                bucket, 
                object_name,
                ExtraArgs=extra_args
            )
            logger.info(f"Uploaded {file_path} to {bucket}/{object_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload {file_path}: {str(e)}")
            return False
    
    def download_file(self, bucket: str, object_name: str, file_path: str) -> bool:
        """Download a file from an S3 bucket.
        
        Args:
            bucket: Bucket to download from
            object_name: S3 object name
            file_path: Local path to save file
            
        Returns:
            True if file was downloaded, False otherwise
        """
        try:
            self.s3_client.download_file(bucket, object_name, file_path)
            logger.info(f"Downloaded {bucket}/{object_name} to {file_path}")
            return True
        except ClientError as e:
            logger.error(f"Failed to download {bucket}/{object_name}: {str(e)}")
            return False
    
    def get_s3_uri(self, bucket: str, object_name: str) -> str:
        """Get the S3 URI for an object.
        
        Args:
            bucket: S3 bucket name
            object_name: S3 object name
            
        Returns:
            S3 URI (s3://bucket/object)
        """
        return f"s3://{bucket}/{object_name}"
    
    def get_presigned_url(self, bucket: str, object_name: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for object access.
        
        Args:
            bucket: S3 bucket name
            object_name: S3 object name
            expiration: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': object_name},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            return None
    
    # DynamoDB operations for sample data
    
    def create_samples_table(self, table_name: str = 'blims-samples') -> bool:
        """Create DynamoDB table for BLIMS samples.
        
        Args:
            table_name: Name for the samples table
            
        Returns:
            True if table was created, False otherwise
        """
        try:
            table = self.dynamodb_resource.create_table(
                TableName=table_name,
                KeySchema=[
                    {'AttributeName': 'sample_id', 'KeyType': 'HASH'},  # Partition key
                ],
                AttributeDefinitions=[
                    {'AttributeName': 'sample_id', 'AttributeType': 'S'},
                ],
                BillingMode='PAY_PER_REQUEST'  # On-demand capacity
            )
            # Wait for table to be created
            table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
            logger.info(f"Created DynamoDB table: {table_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to create DynamoDB table: {str(e)}")
            return False
    
    def put_sample(self, table_name: str, sample_data: Dict[str, Any]) -> bool:
        """Store sample data in DynamoDB.
        
        Args:
            table_name: DynamoDB table name
            sample_data: Sample data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.dynamodb_resource.Table(table_name).put_item(Item=sample_data)
            logger.info(f"Added sample {sample_data.get('sample_id')} to DynamoDB")
            return True
        except ClientError as e:
            logger.error(f"Failed to store sample in DynamoDB: {str(e)}")
            return False
    
    def get_sample(self, table_name: str, sample_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve sample data from DynamoDB.
        
        Args:
            table_name: DynamoDB table name
            sample_id: Sample ID to retrieve
            
        Returns:
            Sample data dictionary or None if not found
        """
        try:
            response = self.dynamodb_resource.Table(table_name).get_item(
                Key={'sample_id': sample_id}
            )
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Failed to get sample from DynamoDB: {str(e)}")
            return None
    
    # AWS Batch operations for bioinformatics analyses
    
    def submit_analysis_job(self, 
                           job_name: str,
                           job_queue: str,
                           job_definition: str,
                           command: Optional[List[str]] = None,
                           parameters: Optional[Dict[str, str]] = None,
                           environment: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """Submit a bioinformatics analysis job to AWS Batch.
        
        Args:
            job_name: Name for the job
            job_queue: AWS Batch job queue name
            job_definition: AWS Batch job definition name/ARN
            command: Command to run (overrides job definition command)
            parameters: Job parameters
            environment: Environment variables
            
        Returns:
            Job ID if submission was successful, None otherwise
        """
        try:
            # Build job submission parameters
            submit_args = {
                'jobName': job_name,
                'jobQueue': job_queue,
                'jobDefinition': job_definition
            }
            
            # Add optional parameters if provided
            if command:
                submit_args['containerOverrides'] = {'command': command}
            
            if parameters:
                submit_args['parameters'] = parameters
                
            if environment:
                if 'containerOverrides' not in submit_args:
                    submit_args['containerOverrides'] = {}
                submit_args['containerOverrides']['environment'] = environment
            
            # Submit the job
            response = self.batch_client.submit_job(**submit_args)
            
            job_id = response['jobId']
            logger.info(f"Submitted AWS Batch job: {job_id}")
            return job_id
            
        except ClientError as e:
            logger.error(f"Failed to submit AWS Batch job: {str(e)}")
            return None
    
    def get_job_status(self, job_id: str) -> Optional[str]:
        """Get the status of an AWS Batch job.
        
        Args:
            job_id: AWS Batch job ID
            
        Returns:
            Job status or None if retrieval failed
        """
        try:
            response = self.batch_client.describe_jobs(jobs=[job_id])
            if response['jobs']:
                return response['jobs'][0]['status']
            return None
        except ClientError as e:
            logger.error(f"Failed to get job status: {str(e)}")
            return None

# Helper functions for common operations

def get_aws_manager(region: str = DEFAULT_REGION) -> AWSManager:
    """Get an AWS Manager instance.
    
    Args:
        region: AWS region to use
        
    Returns:
        Configured AWSManager instance
    """
    return AWSManager(region=region)

def generate_s3_key_for_sample(sample_id: str, file_name: str, analysis_type: Optional[str] = None) -> str:
    """Generate a standardized S3 key for a sample file.
    
    Args:
        sample_id: Sample ID
        file_name: Original filename
        analysis_type: Optional analysis type for organization
        
    Returns:
        Standardized S3 key
    """
    if analysis_type:
        return f"samples/{sample_id}/{analysis_type}/{file_name}"
    return f"samples/{sample_id}/{file_name}"

def create_analysis_job_name(sample_id: str, analysis_type: str) -> str:
    """Create a standardized job name for an analysis job.
    
    Args:
        sample_id: Sample ID
        analysis_type: Type of analysis (e.g., "fastqc", "alignment")
        
    Returns:
        Standardized job name
    """
    timestamp = uuid.uuid4().hex[:8]  # Random identifier for uniqueness
    return f"blims-{analysis_type}-{sample_id}-{timestamp}"