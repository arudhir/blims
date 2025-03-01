"""Job model for BLIMS."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4


class JobStatus(str, Enum):
    """Status of a bioinformatics job."""
    
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class JobType(str, Enum):
    """Types of bioinformatics jobs."""
    
    READ_PROCESSING = "READ_PROCESSING"
    NORMALIZATION = "NORMALIZATION"
    QUANTIFICATION = "QUANTIFICATION"
    ASSEMBLY = "ASSEMBLY"
    ANNOTATION = "ANNOTATION"
    DATABASE_UPDATE = "DATABASE_UPDATE"
    FASTQC = "FASTQC"
    BWA_MEM = "BWA_MEM"
    CUSTOM = "CUSTOM"


class Job:
    """A bioinformatics job in the LIMS system.
    
    Jobs represent computational tasks executed on sample data, such as
    sequence alignment, assembly, or annotation. They track execution status,
    input/output locations, and AWS Batch information.
    """
    
    def __init__(
        self,
        name: str,
        job_type: JobType,
        sample_id: Union[UUID, str],
        created_by: str,
        id: Optional[Union[UUID, str]] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        input_files: Optional[List[Dict[str, str]]] = None,
        output_files: Optional[List[Dict[str, str]]] = None,
        status: JobStatus = JobStatus.PENDING,
        log_url: Optional[str] = None,
        aws_job_id: Optional[str] = None,
        aws_job_definition: Optional[str] = None,
        aws_job_queue: Optional[str] = None,
        parent_job_ids: Optional[List[Union[UUID, str]]] = None,
        child_job_ids: Optional[List[Union[UUID, str]]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ):
        """Initialize a new Job.
        
        Args:
            name: The name of the job
            job_type: The type of bioinformatics job
            sample_id: ID of the sample this job processes
            created_by: The user who created this job
            id: Unique identifier (generated if not provided)
            description: Optional description of the job
            parameters: Parameters used for the job execution
            input_files: List of input files (with paths and descriptions)
            output_files: List of output files (with paths and descriptions)
            status: Current status of the job
            log_url: URL to the job execution logs
            aws_job_id: The AWS Batch job ID if executed on AWS
            aws_job_definition: The AWS Batch job definition ARN
            aws_job_queue: The AWS Batch job queue ARN
            parent_job_ids: IDs of jobs that are prerequisites for this job
            child_job_ids: IDs of jobs that depend on this job
            start_time: When the job started execution
            end_time: When the job finished execution
        """
        self.id = id or uuid4()
        self.name = name
        self.job_type = job_type if isinstance(job_type, JobType) else JobType(job_type)
        self.sample_id = sample_id
        self.created_by = created_by
        self.created_at = datetime.now()
        self.description = description
        self.parameters = parameters or {}
        self.input_files = input_files or []
        self.output_files = output_files or []
        self.status = status if isinstance(status, JobStatus) else JobStatus(status)
        self.log_url = log_url
        self.aws_job_id = aws_job_id
        self.aws_job_definition = aws_job_definition
        self.aws_job_queue = aws_job_queue
        self.parent_job_ids = parent_job_ids or []
        self.child_job_ids = child_job_ids or []
        self.start_time = start_time
        self.end_time = end_time
        
    def update_status(self, status: JobStatus) -> None:
        """Update the job status and timestamps.
        
        Args:
            status: The new job status
        """
        old_status = self.status
        self.status = status if isinstance(status, JobStatus) else JobStatus(status)
        
        # Update timestamps when the job starts or ends
        if old_status != JobStatus.RUNNING and status == JobStatus.RUNNING:
            self.start_time = datetime.now()
        
        if status in [JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED]:
            self.end_time = datetime.now()
    
    def add_parent_job(self, job_id: Union[UUID, str]) -> None:
        """Add a parent job that this job depends on.
        
        Args:
            job_id: The ID of the parent job
        """
        if job_id not in self.parent_job_ids:
            self.parent_job_ids.append(job_id)
    
    def add_child_job(self, job_id: Union[UUID, str]) -> None:
        """Add a child job that depends on this job.
        
        Args:
            job_id: The ID of the child job
        """
        if job_id not in self.child_job_ids:
            self.child_job_ids.append(job_id)
    
    def add_input_file(self, path: str, description: str) -> None:
        """Add an input file to this job.
        
        Args:
            path: Path to the input file (can be S3 URI)
            description: Description of the file
        """
        self.input_files.append({"path": path, "description": description})
    
    def add_output_file(self, path: str, description: str) -> None:
        """Add an output file to this job.
        
        Args:
            path: Path to the output file (can be S3 URI)
            description: Description of the file
        """
        self.output_files.append({"path": path, "description": description})
    
    def update_parameter(self, key: str, value: Any) -> None:
        """Update a job parameter.
        
        Args:
            key: Parameter name
            value: Parameter value
        """
        self.parameters[key] = value
    
    def get_duration(self) -> Optional[float]:
        """Get the job duration in seconds.
        
        Returns:
            Duration in seconds or None if not applicable
        """
        if not self.start_time:
            return None
        
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert this job to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the job
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "job_type": self.job_type.value,
            "sample_id": str(self.sample_id),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "parameters": self.parameters,
            "input_files": self.input_files,
            "output_files": self.output_files,
            "status": self.status.value,
            "log_url": self.log_url,
            "aws_job_id": self.aws_job_id,
            "aws_job_definition": self.aws_job_definition,
            "aws_job_queue": self.aws_job_queue,
            "parent_job_ids": [str(jid) for jid in self.parent_job_ids],
            "child_job_ids": [str(jid) for jid in self.child_job_ids],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.get_duration(),
        }