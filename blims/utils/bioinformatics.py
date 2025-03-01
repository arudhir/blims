"""Bioinformatics utility functions for BLIMS.

This module provides functionality for:
- Managing sequencing data (reads)
- Submitting and monitoring bioinformatics analyses
- Storing and retrieving analysis results
- Connecting analyses to sample records
"""

import os
import logging
import json
import uuid
from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum

from blims.utils.aws_utils import AWSManager, get_aws_manager, generate_s3_key_for_sample, create_analysis_job_name

# Set up logging
logger = logging.getLogger(__name__)

# Get defaults from config
from blims.config import get_s3_bucket, get_batch_job_queue, get_batch_job_definition

# Default S3 bucket for bioinformatics data
DEFAULT_BUCKET = get_s3_bucket("bioinformatics")

# Default AWS Batch queue and job definitions
DEFAULT_JOB_QUEUE = get_batch_job_queue()

class SequencingType(Enum):
    """Types of sequencing data."""
    
    ILLUMINA = "illumina"
    NANOPORE = "nanopore"
    PACBIO = "pacbio"
    OTHER = "other"

class AnalysisType(Enum):
    """Types of bioinformatics analyses."""
    
    FASTQC = "fastqc"
    ALIGNMENT = "alignment"
    VARIANT_CALLING = "variant-calling"
    ASSEMBLY = "assembly"
    TAXONOMIC_PROFILING = "taxonomic-profiling"
    RNA_SEQ = "rna-seq" 
    CUSTOM = "custom"

class FileType(Enum):
    """Types of bioinformatics files."""
    
    FASTQ = "fastq"
    BAM = "bam"
    VCF = "vcf"
    FASTA = "fasta"
    BED = "bed"
    GFF = "gff"
    TSV = "tsv"
    HTML = "html"
    PDF = "pdf"
    OTHER = "other"

class BioinfManager:
    """Manager for bioinformatics operations."""
    
    def __init__(
        self, 
        bucket: str = DEFAULT_BUCKET,
        job_queue: str = DEFAULT_JOB_QUEUE,
        region: str = "us-east-1"
    ):
        """Initialize the bioinformatics manager.
        
        Args:
            bucket: S3 bucket name for storing data
            job_queue: AWS Batch job queue name
            region: AWS region
        """
        self.bucket = bucket
        self.job_queue = job_queue
        self.region = region
        self.aws = get_aws_manager(region=region)
        
        # Ensure bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self) -> None:
        """Ensure the S3 bucket exists, creating it if necessary."""
        try:
            self.aws.s3_client.head_bucket(Bucket=self.bucket)
            logger.info(f"Bucket {self.bucket} exists")
        except:
            logger.info(f"Creating bucket {self.bucket}")
            self.aws.create_bucket(self.bucket)
    
    # Sequencing data management
    
    def upload_reads(
        self, 
        sample_id: str, 
        file_path: str, 
        sequencing_type: Union[SequencingType, str] = SequencingType.ILLUMINA,
        file_type: Union[FileType, str] = FileType.FASTQ,
        metadata: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, str]:
        """Upload sequencing reads for a sample.
        
        Args:
            sample_id: Sample ID
            file_path: Path to the file
            sequencing_type: Type of sequencing data
            file_type: Type of file
            metadata: Additional metadata to store with the file
            
        Returns:
            Tuple of (success status, S3 key)
        """
        # Convert enum to string if needed
        if isinstance(sequencing_type, SequencingType):
            sequencing_type = sequencing_type.value
            
        if isinstance(file_type, FileType):
            file_type = file_type.value
        
        # Generate S3 key for the file
        file_name = os.path.basename(file_path)
        s3_key = f"samples/{sample_id}/reads/{sequencing_type}/{file_name}"
        
        # Prepare metadata
        file_metadata = metadata or {}
        file_metadata.update({
            "sample_id": sample_id,
            "sequencing_type": sequencing_type,
            "file_type": file_type
        })
        
        # Upload the file
        success = self.aws.upload_file(
            file_path=file_path,
            bucket=self.bucket,
            object_name=s3_key,
            metadata=file_metadata
        )
        
        return success, s3_key
    
    def get_reads_url(self, sample_id: str, file_name: str, sequencing_type: Union[SequencingType, str] = SequencingType.ILLUMINA) -> Optional[str]:
        """Get a presigned URL for accessing sequencing reads.
        
        Args:
            sample_id: Sample ID
            file_name: Name of the file
            sequencing_type: Type of sequencing data
            
        Returns:
            Presigned URL or None if failed
        """
        # Convert enum to string if needed
        if isinstance(sequencing_type, SequencingType):
            sequencing_type = sequencing_type.value
            
        # Generate S3 key
        s3_key = f"samples/{sample_id}/reads/{sequencing_type}/{file_name}"
        
        # Generate URL
        return self.aws.get_presigned_url(self.bucket, s3_key)
    
    # Analysis management
    
    def submit_analysis(
        self,
        sample_id: str,
        analysis_type: Union[AnalysisType, str],
        job_definition: str,
        input_files: List[str],
        parameters: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """Submit a bioinformatics analysis job.
        
        Args:
            sample_id: Sample ID
            analysis_type: Type of analysis
            job_definition: AWS Batch job definition name/ARN
            input_files: List of input file S3 URIs
            parameters: Additional parameters for the job
            environment: Environment variables for the job
            
        Returns:
            Job ID if submission was successful, None otherwise
        """
        # Convert enum to string if needed
        if isinstance(analysis_type, AnalysisType):
            analysis_type = analysis_type.value
        
        # Create job name
        job_name = create_analysis_job_name(sample_id, analysis_type)
        
        # Prepare job parameters
        job_params = parameters or {}
        job_params.update({
            "sample_id": sample_id,
            "analysis_type": analysis_type,
            "input_files": ",".join(input_files),
            "output_bucket": self.bucket,
            "output_prefix": f"samples/{sample_id}/analyses/{analysis_type}/"
        })
        
        # Prepare environment variables
        env_vars = []
        if environment:
            for key, value in environment.items():
                env_vars.append({"name": key, "value": value})
        
        # Submit the job
        return self.aws.submit_analysis_job(
            job_name=job_name,
            job_queue=self.job_queue,
            job_definition=job_definition,
            parameters=job_params,
            environment=env_vars if env_vars else None
        )
    
    def check_analysis_status(self, job_id: str) -> Optional[str]:
        """Check the status of an analysis job.
        
        Args:
            job_id: AWS Batch job ID
            
        Returns:
            Job status or None if retrieval failed
        """
        return self.aws.get_job_status(job_id)
    
    def get_analysis_results(self, sample_id: str, analysis_type: Union[AnalysisType, str]) -> List[Dict[str, Any]]:
        """Get the list of analysis result files.
        
        Args:
            sample_id: Sample ID
            analysis_type: Type of analysis
            
        Returns:
            List of file metadata dictionaries
        """
        # Convert enum to string if needed
        if isinstance(analysis_type, AnalysisType):
            analysis_type = analysis_type.value
            
        # Generate prefix for listing objects
        prefix = f"samples/{sample_id}/analyses/{analysis_type}/"
        
        try:
            # List objects with the prefix
            response = self.aws.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            
            results = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    # Get file metadata
                    obj_response = self.aws.s3_client.head_object(
                        Bucket=self.bucket,
                        Key=key
                    )
                    
                    # Extract metadata
                    metadata = obj_response.get('Metadata', {})
                    file_info = {
                        "key": key,
                        "size": obj['Size'],
                        "last_modified": obj['LastModified'].isoformat(),
                        "metadata": metadata,
                        "file_name": os.path.basename(key)
                    }
                    results.append(file_info)
                    
            return results
        except Exception as e:
            logger.error(f"Error retrieving analysis results: {str(e)}")
            return []
    
    def get_analysis_result_url(self, sample_id: str, analysis_type: Union[AnalysisType, str], file_name: str) -> Optional[str]:
        """Get a presigned URL for an analysis result file.
        
        Args:
            sample_id: Sample ID
            analysis_type: Type of analysis
            file_name: Name of the file
            
        Returns:
            Presigned URL or None if failed
        """
        # Convert enum to string if needed
        if isinstance(analysis_type, AnalysisType):
            analysis_type = analysis_type.value
            
        # Generate S3 key
        s3_key = f"samples/{sample_id}/analyses/{analysis_type}/{file_name}"
        
        # Generate URL
        return self.aws.get_presigned_url(self.bucket, s3_key)
    
    # Helper functions
    
    def list_sample_data(self, sample_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """List all data associated with a sample.
        
        Args:
            sample_id: Sample ID
            
        Returns:
            Dictionary with reads and analyses data
        """
        try:
            # List objects with the sample prefix
            prefix = f"samples/{sample_id}/"
            response = self.aws.s3_client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            
            # Organize results
            result = {
                "reads": {},
                "analyses": {}
            }
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    parts = key.split('/')
                    
                    # Skip if we don't have enough parts
                    if len(parts) < 4:
                        continue
                    
                    # Organize by data type
                    if 'reads' in key:
                        seq_type = parts[3]  # e.g., "illumina", "nanopore"
                        if seq_type not in result["reads"]:
                            result["reads"][seq_type] = []
                        
                        file_info = {
                            "key": key,
                            "file_name": os.path.basename(key),
                            "size": obj['Size'],
                            "last_modified": obj['LastModified'].isoformat()
                        }
                        result["reads"][seq_type].append(file_info)
                        
                    elif 'analyses' in key:
                        analysis_type = parts[3]  # e.g., "fastqc", "alignment"
                        if analysis_type not in result["analyses"]:
                            result["analyses"][analysis_type] = []
                        
                        file_info = {
                            "key": key,
                            "file_name": os.path.basename(key),
                            "size": obj['Size'],
                            "last_modified": obj['LastModified'].isoformat()
                        }
                        result["analyses"][analysis_type].append(file_info)
            
            return result
        except Exception as e:
            logger.error(f"Error listing sample data: {str(e)}")
            return {"reads": {}, "analyses": {}}

# Helper functions

def get_bioinf_manager(
    bucket: str = DEFAULT_BUCKET,
    job_queue: str = DEFAULT_JOB_QUEUE,
    region: str = "us-east-1"
) -> BioinfManager:
    """Get a bioinformatics manager instance.
    
    Args:
        bucket: S3 bucket name
        job_queue: AWS Batch job queue name
        region: AWS region
        
    Returns:
        Configured BioinfManager instance
    """
    return BioinfManager(bucket=bucket, job_queue=job_queue, region=region)

def get_file_extension(file_path: str) -> str:
    """Get the file extension from a path.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension without the dot
    """
    _, ext = os.path.splitext(file_path)
    return ext.lstrip('.')

def detect_file_type(file_path: str) -> FileType:
    """Detect the file type from the file extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        FileType enum value
    """
    ext = get_file_extension(file_path).lower()
    
    # Common bioinformatics file extensions
    if ext in ['fastq', 'fq', 'fastq.gz', 'fq.gz']:
        return FileType.FASTQ
    elif ext in ['bam', 'sam']:
        return FileType.BAM
    elif ext in ['vcf', 'vcf.gz']:
        return FileType.VCF
    elif ext in ['fa', 'fasta', 'fna', 'faa']:
        return FileType.FASTA
    elif ext in ['bed']:
        return FileType.BED  
    elif ext in ['gff', 'gtf', 'gff3']:
        return FileType.GFF
    elif ext in ['tsv', 'csv', 'txt']:
        return FileType.TSV
    elif ext in ['html', 'htm']:
        return FileType.HTML
    elif ext in ['pdf']:
        return FileType.PDF
    else:
        return FileType.OTHER