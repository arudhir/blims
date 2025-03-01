"""Analysis service for handling bioinformatics analysis operations."""

import os
import logging
import json
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from blims.core.repository import SampleRepository
from blims.models.sample import Sample
from blims.models.analysis import Analysis, AnalysisStatus
from blims.utils.aws_utils import get_aws_manager
from blims.utils.bioinformatics import (
    get_bioinf_manager, 
    AnalysisType, 
    SequencingType,
    FileType,
    generate_s3_key_for_sample
)

# Set up logging
logger = logging.getLogger(__name__)

# Get default values from config
from blims.config import get_aws_region, get_s3_bucket, get_batch_job_queue

# Default values
DEFAULT_BUCKET = get_s3_bucket("bioinformatics")
DEFAULT_REGION = get_aws_region()
DEFAULT_JOB_QUEUE = get_batch_job_queue()


class AnalysisService:
    """Service for managing bioinformatics analyses in BLIMS."""
    
    def __init__(
        self,
        sample_repository: Optional[SampleRepository] = None,
        bucket: str = DEFAULT_BUCKET,
        region: str = DEFAULT_REGION,
        job_queue: str = DEFAULT_JOB_QUEUE
    ):
        """Initialize the analysis service.
        
        Args:
            sample_repository: Repository for sample data
            bucket: S3 bucket name for bioinformatics data
            region: AWS region
            job_queue: AWS Batch job queue
        """
        self.repository = sample_repository or SampleRepository()
        self.bucket = bucket
        self.region = region
        self.job_queue = job_queue
        
        # Initialize managers
        self.bioinf = get_bioinf_manager(bucket=bucket, job_queue=job_queue, region=region)
        self.aws = get_aws_manager(region=region)
        
        # Analysis registry: job_id -> (analysis, sample_id)
        self._active_analyses = {}
    
    # Data Management
    
    def upload_sequencing_data(
        self,
        sample_id: Union[UUID, str],
        file_path: str,
        sequencing_type: Union[str, SequencingType] = SequencingType.ILLUMINA,
        file_type: Union[str, FileType] = FileType.FASTQ,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Upload sequencing data for a sample.
        
        Args:
            sample_id: Sample ID
            file_path: Path to the sequencing data file
            sequencing_type: Type of sequencing data
            file_type: Type of file
            metadata: Additional metadata
            
        Returns:
            Information about the uploaded data
            
        Raises:
            ValueError: If sample not found or upload fails
        """
        # Verify sample exists
        sample = self._get_sample(sample_id)
        if not sample:
            raise ValueError(f"Sample with ID {sample_id} not found")
        
        # Upload the data
        success, s3_key = self.bioinf.upload_reads(
            sample_id=str(sample.sample_id),
            file_path=file_path,
            sequencing_type=sequencing_type,
            file_type=file_type,
            metadata=metadata
        )
        
        if not success:
            raise ValueError(f"Failed to upload {file_path}")
        
        # Create data record
        data_info = {
            "type": str(sequencing_type.value) if hasattr(sequencing_type, "value") else str(sequencing_type),
            "file_type": str(file_type.value) if hasattr(file_type, "value") else str(file_type),
            "file_name": os.path.basename(file_path),
            "s3_key": s3_key,
            "s3_bucket": self.bucket,
            "s3_uri": f"s3://{self.bucket}/{s3_key}",
            "size": os.path.getsize(file_path),
            "metadata": metadata or {}
        }
        
        # Add to sample record
        sample.add_sequencing_data(data_info)
        
        return data_info
    
    def get_sequencing_data_url(
        self,
        sample_id: Union[UUID, str],
        file_name: str,
        expiry: int = 3600
    ) -> str:
        """Get a presigned URL for sequencing data.
        
        Args:
            sample_id: Sample ID
            file_name: Name of the file
            expiry: Expiry time in seconds
            
        Returns:
            Presigned URL
            
        Raises:
            ValueError: If sample or file not found
        """
        # Verify sample exists
        sample = self._get_sample(sample_id)
        if not sample:
            raise ValueError(f"Sample with ID {sample_id} not found")
        
        # Find the file in the sample's sequencing data
        s3_key = None
        for data in sample.sequencing_data:
            if data.get("file_name") == file_name:
                s3_key = data.get("s3_key")
                break
        
        if not s3_key:
            raise ValueError(f"File {file_name} not found in sample {sample_id}")
        
        # Generate URL
        url = self.aws.get_presigned_url(
            bucket=self.bucket,
            object_name=s3_key,
            expiration=expiry
        )
        
        if not url:
            raise ValueError(f"Failed to generate URL for {file_name}")
        
        return url
    
    # Analysis Management
    
    def start_analysis(
        self,
        sample_id: Union[UUID, str],
        analysis_type: Union[str, AnalysisType],
        analysis_name: str,
        job_definition: str,
        input_files: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        created_by: str = "system"
    ) -> Analysis:
        """Start a bioinformatics analysis for a sample.
        
        Args:
            sample_id: Sample ID
            analysis_type: Type of analysis to run
            analysis_name: Name for the analysis
            job_definition: AWS Batch job definition
            input_files: Input file S3 URIs (if None, uses all sequencing data)
            parameters: Analysis parameters
            created_by: User starting the analysis
            
        Returns:
            The created Analysis object
            
        Raises:
            ValueError: If sample not found or job submission fails
        """
        # Verify sample exists
        sample = self._get_sample(sample_id)
        if not sample:
            raise ValueError(f"Sample with ID {sample_id} not found")
        
        # Create analysis object
        analysis = Analysis(
            name=analysis_name,
            analysis_type=str(analysis_type.value) if hasattr(analysis_type, "value") else str(analysis_type),
            sample_id=sample.id,
            created_by=created_by,
            input_files=input_files or [],
            parameters=parameters or {},
            status=AnalysisStatus.PENDING
        )
        
        # If no input files specified, use all sequencing data for the sample
        if not input_files:
            input_files = [
                data["s3_uri"] for data in sample.sequencing_data 
                if "s3_uri" in data
            ]
            
            if not input_files:
                raise ValueError(f"No sequencing data found for sample {sample_id}")
            
            analysis.input_files = input_files
        
        # Submit the analysis job
        job_id = self.bioinf.submit_analysis(
            sample_id=str(sample.sample_id),
            analysis_type=analysis.analysis_type,
            job_definition=job_definition,
            input_files=input_files,
            parameters=parameters
        )
        
        if not job_id:
            raise ValueError(f"Failed to submit analysis job for sample {sample_id}")
        
        # Update analysis with job ID and status
        analysis.job_id = job_id
        analysis.update_status(AnalysisStatus.RUNNING)
        
        # Register this analysis in the active analyses
        self._active_analyses[job_id] = (analysis, sample.id)
        
        # Add to sample
        sample.add_analysis({
            "id": str(analysis.id),
            "name": analysis.name,
            "type": analysis.analysis_type,
            "status": analysis.status.value,
            "job_id": analysis.job_id,
            "started_at": analysis.started_at.isoformat() if analysis.started_at else None
        })
        
        return analysis
    
    def get_analysis_status(
        self,
        job_id: str
    ) -> Optional[AnalysisStatus]:
        """Get the status of an analysis job.
        
        Args:
            job_id: AWS Batch job ID
            
        Returns:
            Current status or None if not found
        """
        if job_id not in self._active_analyses:
            return None
        
        # Get current status from AWS
        status_str = self.bioinf.check_analysis_status(job_id)
        
        if not status_str:
            return None
        
        # Map AWS Batch status to our AnalysisStatus
        status_map = {
            "SUBMITTED": AnalysisStatus.PENDING,
            "PENDING": AnalysisStatus.PENDING,
            "RUNNABLE": AnalysisStatus.PENDING,
            "STARTING": AnalysisStatus.RUNNING,
            "RUNNING": AnalysisStatus.RUNNING,
            "SUCCEEDED": AnalysisStatus.SUCCEEDED,
            "FAILED": AnalysisStatus.FAILED
        }
        
        status = status_map.get(status_str, AnalysisStatus.RUNNING)
        
        # Update our local record
        analysis, sample_id = self._active_analyses[job_id]
        
        # If status changed and it's a terminal status, update sample and remove from active
        if status != analysis.status and status in [AnalysisStatus.SUCCEEDED, AnalysisStatus.FAILED]:
            analysis.update_status(status)
            
            # Update sample record
            sample = self._get_sample(sample_id)
            if sample:
                # Find and update the analysis record in the sample
                for analysis_dict in sample.analyses:
                    if analysis_dict.get("job_id") == job_id:
                        analysis_dict["status"] = status.value
                        analysis_dict["completed_at"] = analysis.completed_at.isoformat()
                        break
            
            # If succeeded, collect output files
            if status == AnalysisStatus.SUCCEEDED:
                self._collect_analysis_results(analysis, sample)
                
            # Remove from active analyses if complete
            del self._active_analyses[job_id]
        
        return status
    
    def _collect_analysis_results(self, analysis: Analysis, sample: Sample) -> None:
        """Collect analysis results and update records.
        
        Args:
            analysis: Analysis object
            sample: Sample object
        """
        # Get analysis results
        results = self.bioinf.get_analysis_results(
            sample_id=str(sample.sample_id),
            analysis_type=analysis.analysis_type
        )
        
        # Add output files to analysis
        for result in results:
            file_info = {
                "file_name": result["file_name"],
                "s3_key": result["key"],
                "s3_bucket": self.bucket,
                "s3_uri": f"s3://{self.bucket}/{result['key']}",
                "size": result["size"],
                "last_modified": result["last_modified"],
                "metadata": result.get("metadata", {})
            }
            
            analysis.add_output_file(file_info)
            
            # Find and update the analysis record in the sample
            for analysis_dict in sample.analyses:
                if analysis_dict.get("id") == str(analysis.id):
                    if "output_files" not in analysis_dict:
                        analysis_dict["output_files"] = []
                    analysis_dict["output_files"].append(file_info)
                    break
    
    def get_analysis_result_url(
        self,
        sample_id: Union[UUID, str],
        analysis_id: Union[UUID, str],
        file_name: str,
        expiry: int = 3600
    ) -> str:
        """Get a presigned URL for an analysis result file.
        
        Args:
            sample_id: Sample ID
            analysis_id: Analysis ID
            file_name: Name of the file
            expiry: Expiry time in seconds
            
        Returns:
            Presigned URL
            
        Raises:
            ValueError: If sample, analysis, or file not found
        """
        # Verify sample exists
        sample = self._get_sample(sample_id)
        if not sample:
            raise ValueError(f"Sample with ID {sample_id} not found")
        
        # Find the analysis in the sample's analyses
        analysis_type = None
        s3_key = None
        
        for analysis in sample.analyses:
            if analysis.get("id") == str(analysis_id):
                analysis_type = analysis.get("type")
                if "output_files" in analysis:
                    for file_info in analysis["output_files"]:
                        if file_info.get("file_name") == file_name:
                            s3_key = file_info.get("s3_key")
                            break
                break
        
        if not analysis_type:
            raise ValueError(f"Analysis {analysis_id} not found for sample {sample_id}")
            
        if not s3_key:
            # Try to generate the key based on naming convention
            s3_key = f"samples/{sample.sample_id}/analyses/{analysis_type}/{file_name}"
            
        # Generate URL
        url = self.aws.get_presigned_url(
            bucket=self.bucket,
            object_name=s3_key,
            expiration=expiry
        )
        
        if not url:
            raise ValueError(f"Failed to generate URL for {file_name}")
        
        return url
    
    # Helper methods
    
    def _get_sample(self, sample_id: Union[UUID, str]) -> Optional[Sample]:
        """Get a sample by ID.
        
        Args:
            sample_id: Sample ID (UUID or string)
            
        Returns:
            Sample object or None if not found
        """
        # Convert to UUID if it's a string
        if isinstance(sample_id, str):
            try:
                sample_id = UUID(sample_id)
            except ValueError:
                # If it's not a valid UUID, it might be a sample_id like "s1"
                # Find it in the repository
                for sample in self.repository.get_all():
                    if sample.sample_id == sample_id:
                        return sample
                return None
        
        return self.repository.get(sample_id)