"""Service for managing bioinformatics jobs."""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import boto3

from blims.models.job import Job, JobStatus, JobType
from blims.repositories.job_repository import JobRepository
from blims.services.sample_service import SampleService


class JobService:
    """Service for managing bioinformatics jobs.
    
    This service provides business logic for creating, submitting,
    and monitoring bioinformatics jobs.
    """
    
    def __init__(
        self, 
        job_repository: JobRepository,
        sample_service: SampleService,
        aws_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the job service.
        
        Args:
            job_repository: Repository for job persistence
            sample_service: Service for sample operations
            aws_config: Optional AWS configuration dictionary
        """
        self.job_repository = job_repository
        self.sample_service = sample_service
        self.aws_config = aws_config or {}
        
        # Set up AWS Batch client if config is provided
        self.batch_client = None
        if aws_config and 'region' in aws_config:
            self.batch_client = boto3.client('batch', region_name=aws_config.get('region'))
    
    def create_job(self, job_data: Dict[str, Any]) -> Job:
        """Create a new job.
        
        Args:
            job_data: Dictionary with job information
            
        Returns:
            The created job
            
        Raises:
            ValueError: If required fields are missing or sample does not exist
        """
        # Validate required fields
        required_fields = ['name', 'job_type', 'sample_id', 'created_by']
        for field in required_fields:
            if field not in job_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate sample exists
        sample_id = job_data['sample_id']
        sample = self.sample_service.get_sample(sample_id)
        if not sample:
            raise ValueError(f"Sample with ID {sample_id} not found")
        
        # Create job
        job = Job(
            name=job_data['name'],
            job_type=job_data['job_type'],
            sample_id=sample_id,
            created_by=job_data['created_by'],
            description=job_data.get('description'),
            parameters=job_data.get('parameters', {}),
            input_files=job_data.get('input_files', []),
            output_files=job_data.get('output_files', []),
        )
        
        return self.job_repository.create_job(job)
    
    def get_job(self, job_id: Union[str, uuid.UUID]) -> Optional[Job]:
        """Get a job by ID.
        
        Args:
            job_id: The ID of the job to retrieve
            
        Returns:
            The job if found, None otherwise
        """
        return self.job_repository.get_job(job_id)
    
    def get_all_jobs(self) -> List[Job]:
        """Get all jobs.
        
        Returns:
            List of all jobs
        """
        return self.job_repository.get_all_jobs()
    
    def get_jobs_by_sample(self, sample_id: Union[str, uuid.UUID]) -> List[Job]:
        """Get all jobs for a specific sample.
        
        Args:
            sample_id: The ID of the sample
            
        Returns:
            List of jobs for the sample
        """
        return self.job_repository.get_jobs_by_sample(sample_id)
    
    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        """Get all jobs with a specific status.
        
        Args:
            status: The status to filter by
            
        Returns:
            List of jobs with the specified status
        """
        return self.job_repository.get_jobs_by_status(status)
    
    def update_job_status(self, job_id: Union[str, uuid.UUID], status: JobStatus) -> Job:
        """Update the status of a job.
        
        Args:
            job_id: The ID of the job to update
            status: The new status
            
        Returns:
            The updated job
            
        Raises:
            ValueError: If the job doesn't exist
        """
        return self.job_repository.update_job_status(job_id, status)
    
    def delete_job(self, job_id: Union[str, uuid.UUID]) -> bool:
        """Delete a job.
        
        Args:
            job_id: The ID of the job to delete
            
        Returns:
            True if the job was deleted, False if it didn't exist
        """
        return self.job_repository.delete_job(job_id)
    
    def submit_job_to_aws(self, job_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        """Submit a job to AWS Batch.
        
        Args:
            job_id: The ID of the job to submit
            
        Returns:
            Dictionary with submission information
            
        Raises:
            ValueError: If the job doesn't exist or AWS Batch is not configured
            RuntimeError: If the job submission fails
        """
        if not self.batch_client:
            raise ValueError("AWS Batch is not configured")
            
        job = self.job_repository.get_job(job_id)
        if not job:
            raise ValueError(f"Job with ID {job_id} not found")
        
        # Get the appropriate job definition based on job type
        job_def_key = job.job_type.value.lower()
        job_definitions = self.aws_config.get('batch', {}).get('job_definitions', {})
        
        if job_def_key not in job_definitions:
            raise ValueError(f"No AWS job definition found for job type: {job.job_type.value}")
            
        job_definition = job_definitions[job_def_key]
        job_queue = self.aws_config.get('batch', {}).get('job_queue')
        
        if not job_queue:
            raise ValueError("No AWS job queue configured")
        
        # Prepare parameters for AWS Batch
        parameters = {}
        command_override = None
        
        # Different job types need different parameter mappings
        if job.job_type == JobType.READ_PROCESSING:
            parameters = {
                'sra_accession': job.parameters.get('sra_accession', ''),
                'output_prefix': job.parameters.get('output_prefix', ''),
                'reference_bucket': self.aws_config.get('s3', {}).get('bioinformatics_bucket', ''),
                'rrna_reference': job.parameters.get('rrna_reference', ''),
                'output_bucket': self.aws_config.get('s3', {}).get('bioinformatics_bucket', '')
            }
        elif job.job_type == JobType.NORMALIZATION:
            command_override = "/usr/local/bin/normalize_reads.sh"
            parameters = {
                'input_bucket': self.aws_config.get('s3', {}).get('bioinformatics_bucket', ''),
                'input_prefix': job.parameters.get('input_prefix', ''),
                'output_bucket': self.aws_config.get('s3', {}).get('bioinformatics_bucket', ''),
                'output_prefix': job.parameters.get('output_prefix', ''),
                'target_depth': job.parameters.get('target_depth', '100'),
                'min_depth': job.parameters.get('min_depth', '5')
            }
        # Add other job types as needed
            
        try:
            # Submit job to AWS Batch
            submit_args = {
                'jobName': f"blims-{job.job_type.value.lower()}-{str(job.id)[:8]}",
                'jobQueue': job_queue,
                'jobDefinition': job_definition,
            }
            
            if parameters:
                submit_args['parameters'] = parameters
                
            if command_override:
                submit_args['containerOverrides'] = {
                    'command': [command_override]
                }
                
            response = self.batch_client.submit_job(**submit_args)
            
            # Update job with AWS information
            job.aws_job_id = response['jobId']
            job.aws_job_definition = job_definition
            job.aws_job_queue = job_queue
            job.update_status(JobStatus.SUBMITTED)
            
            self.job_repository.update_job(job)
            
            return {
                'job_id': str(job.id),
                'aws_job_id': job.aws_job_id,
                'status': job.status.value
            }
            
        except Exception as e:
            raise RuntimeError(f"Failed to submit job to AWS Batch: {str(e)}")
    
    def sync_aws_job_status(self, job_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        """Sync a job's status from AWS Batch.
        
        Args:
            job_id: The ID of the job to sync
            
        Returns:
            Dictionary with synced job information
            
        Raises:
            ValueError: If the job doesn't exist or AWS Batch is not configured
            RuntimeError: If the status sync fails
        """
        if not self.batch_client:
            raise ValueError("AWS Batch is not configured")
            
        job = self.job_repository.get_job(job_id)
        if not job:
            raise ValueError(f"Job with ID {job_id} not found")
            
        if not job.aws_job_id:
            raise ValueError(f"Job with ID {job_id} has not been submitted to AWS")
            
        try:
            # Get job status from AWS Batch
            response = self.batch_client.describe_jobs(jobs=[job.aws_job_id])
            
            if not response['jobs']:
                raise ValueError(f"AWS job with ID {job.aws_job_id} not found")
                
            aws_job = response['jobs'][0]
            aws_status = aws_job['status']
            
            # Map AWS status to our status enum
            status_map = {
                'SUBMITTED': JobStatus.SUBMITTED,
                'PENDING': JobStatus.PENDING,
                'RUNNABLE': JobStatus.PENDING,
                'STARTING': JobStatus.PENDING,
                'RUNNING': JobStatus.RUNNING,
                'SUCCEEDED': JobStatus.SUCCEEDED,
                'FAILED': JobStatus.FAILED
            }
            
            if aws_status in status_map:
                job.update_status(status_map[aws_status])
                
                # Update job with additional AWS information
                if 'logStreamName' in aws_job['container']:
                    log_stream = aws_job['container']['logStreamName']
                    region = self.aws_config.get('region', 'us-east-1')
                    job.log_url = (
                        f"https://{region}.console.aws.amazon.com/cloudwatch/home?"
                        f"region={region}#logsV2:log-groups/log-group/"
                        f"/aws/batch/job/log-stream/{log_stream}"
                    )
                
                self.job_repository.update_job(job)
            
            return {
                'job_id': str(job.id),
                'aws_job_id': job.aws_job_id,
                'status': job.status.value,
                'aws_status': aws_status,
                'log_url': job.log_url
            }
            
        except Exception as e:
            raise RuntimeError(f"Failed to sync AWS job status: {str(e)}")
    
    def sync_all_aws_jobs(self) -> List[Dict[str, Any]]:
        """Sync status of all submitted AWS jobs.
        
        Returns:
            List of dictionaries with synced job information
            
        Raises:
            ValueError: If AWS Batch is not configured
        """
        if not self.batch_client:
            raise ValueError("AWS Batch is not configured")
            
        # Get all jobs that have AWS job IDs and are not in a terminal state
        active_states = [JobStatus.PENDING, JobStatus.SUBMITTED, JobStatus.RUNNING]
        jobs = [job for job in self.get_all_jobs() 
                if job.aws_job_id and job.status in active_states]
        
        results = []
        for job in jobs:
            try:
                result = self.sync_aws_job_status(job.id)
                results.append(result)
            except Exception as e:
                # Log error but continue with other jobs
                results.append({
                    'job_id': str(job.id),
                    'aws_job_id': job.aws_job_id,
                    'status': job.status.value,
                    'error': str(e)
                })
                
        return results
    
    def create_rna_seq_pipeline(
        self, 
        sample_id: Union[str, uuid.UUID], 
        sra_accession: str,
        username: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Job]:
        """Create a complete RNA-Seq pipeline for a sample.
        
        This method creates a series of linked jobs that form the complete
        RNA-Seq pipeline:
        1. Read Processing
        2. Normalization
        3. Quantification
        4. Assembly
        5. Annotation
        6. Database Update
        
        Args:
            sample_id: The ID of the sample to process
            sra_accession: The SRA accession number
            username: The user creating the pipeline
            parameters: Optional additional parameters
            
        Returns:
            List of created job objects
            
        Raises:
            ValueError: If the sample doesn't exist
        """
        parameters = parameters or {}
        
        # Validate sample exists
        sample = self.sample_service.get_sample(sample_id)
        if not sample:
            raise ValueError(f"Sample with ID {sample_id} not found")
        
        # Create base output prefix
        output_prefix = f"samples/{str(sample_id)}/rna-seq/{sra_accession}"
        
        # Create read processing job
        read_job = Job(
            name=f"RNA-Seq Read Processing: {sra_accession}",
            job_type=JobType.READ_PROCESSING,
            sample_id=sample_id,
            created_by=username,
            description=f"Process RNA-Seq reads from SRA accession {sra_accession}",
            parameters={
                'sra_accession': sra_accession,
                'output_prefix': f"{output_prefix}/processing",
                'rrna_reference': parameters.get('rrna_reference', 'references/rrna/rrna_reference.fa')
            }
        )
        read_job = self.job_repository.create_job(read_job)
        
        # Create normalization job
        norm_job = Job(
            name=f"RNA-Seq Normalization: {sra_accession}",
            job_type=JobType.NORMALIZATION,
            sample_id=sample_id,
            created_by=username,
            description=f"Normalize RNA-Seq reads from {sra_accession}",
            parameters={
                'input_prefix': f"{output_prefix}/processing",
                'output_prefix': f"{output_prefix}/normalization",
                'target_depth': parameters.get('target_depth', '100'),
                'min_depth': parameters.get('min_depth', '5')
            },
            parent_job_ids=[read_job.id]
        )
        norm_job = self.job_repository.create_job(norm_job)
        read_job.add_child_job(norm_job.id)
        self.job_repository.update_job(read_job)
        
        # Create quantification job (can run in parallel with assembly)
        quant_job = Job(
            name=f"RNA-Seq Quantification: {sra_accession}",
            job_type=JobType.QUANTIFICATION,
            sample_id=sample_id,
            created_by=username,
            description=f"Quantify RNA-Seq expression from {sra_accession}",
            parameters={
                'input_prefix': f"{output_prefix}/normalization",
                'output_prefix': f"{output_prefix}/quantification",
                'reference_index': parameters.get('reference_index', 'references/transcriptome/index')
            },
            parent_job_ids=[norm_job.id]
        )
        quant_job = self.job_repository.create_job(quant_job)
        norm_job.add_child_job(quant_job.id)
        self.job_repository.update_job(norm_job)
        
        # Create assembly job
        assembly_job = Job(
            name=f"RNA-Seq Assembly: {sra_accession}",
            job_type=JobType.ASSEMBLY,
            sample_id=sample_id,
            created_by=username,
            description=f"Assemble transcripts from {sra_accession}",
            parameters={
                'input_prefix': f"{output_prefix}/normalization",
                'output_prefix': f"{output_prefix}/assembly"
            },
            parent_job_ids=[norm_job.id]
        )
        assembly_job = self.job_repository.create_job(assembly_job)
        norm_job.add_child_job(assembly_job.id)
        self.job_repository.update_job(norm_job)
        
        # Create annotation job
        annot_job = Job(
            name=f"RNA-Seq Annotation: {sra_accession}",
            job_type=JobType.ANNOTATION,
            sample_id=sample_id,
            created_by=username,
            description=f"Annotate transcripts from {sra_accession}",
            parameters={
                'input_prefix': f"{output_prefix}/assembly",
                'output_prefix': f"{output_prefix}/annotation",
                'eggnog_db_path': parameters.get('eggnog_db_path', 'references/eggnog')
            },
            parent_job_ids=[assembly_job.id]
        )
        annot_job = self.job_repository.create_job(annot_job)
        assembly_job.add_child_job(annot_job.id)
        self.job_repository.update_job(assembly_job)
        
        # Create database update job
        db_job = Job(
            name=f"RNA-Seq Database Update: {sra_accession}",
            job_type=JobType.DATABASE_UPDATE,
            sample_id=sample_id,
            created_by=username,
            description=f"Update database with {sra_accession} results",
            parameters={
                'input_prefix': f"{output_prefix}",
                'db_path': parameters.get('db_path', 'database/rna-seq')
            },
            parent_job_ids=[quant_job.id, annot_job.id]
        )
        db_job = self.job_repository.create_job(db_job)
        quant_job.add_child_job(db_job.id)
        annot_job.add_child_job(db_job.id)
        self.job_repository.update_job(quant_job)
        self.job_repository.update_job(annot_job)
        
        # Create list of all jobs in the pipeline
        pipeline_jobs = [read_job, norm_job, quant_job, assembly_job, annot_job, db_job]
        
        # Update sample with analysis info
        sample.add_analysis({
            'type': 'rna-seq',
            'sra_accession': sra_accession,
            'pipeline_jobs': [str(job.id) for job in pipeline_jobs],
            'created_at': datetime.now().isoformat(),
            'created_by': username,
            'status': 'created'
        })
        self.sample_service.update_sample(sample)
        
        return pipeline_jobs