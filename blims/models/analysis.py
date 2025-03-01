"""Analysis models for BLIMS."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4


class AnalysisStatus(Enum):
    """Status of an analysis."""
    
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class Analysis:
    """An analysis in the LIMS system.
    
    Represents a bioinformatics analysis run on sample data.
    """
    
    def __init__(
        self,
        name: str,
        analysis_type: str,
        sample_id: Union[UUID, str],
        created_by: str,
        id: Optional[UUID] = None,
        job_id: Optional[str] = None,
        status: AnalysisStatus = AnalysisStatus.PENDING,
        input_files: Optional[List[str]] = None,
        output_files: Optional[List[Dict[str, Any]]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a new Analysis.
        
        Args:
            name: Name of the analysis
            analysis_type: Type of analysis (e.g., fastqc, alignment)
            sample_id: ID of the sample this analysis is for
            created_by: User who created this analysis
            id: Unique ID (generated if not provided)
            job_id: External job ID (e.g., AWS Batch ID)
            status: Current status of the analysis
            input_files: List of input file paths/URIs
            output_files: List of output file information
            parameters: Parameters used for the analysis
            started_at: When the analysis started
            completed_at: When the analysis completed
            metadata: Additional metadata
        """
        self.id = id or uuid4()
        self.name = name
        self.analysis_type = analysis_type
        self.sample_id = sample_id
        self.created_by = created_by
        self.created_at = datetime.now()
        self.job_id = job_id
        self.status = status
        self.input_files = input_files or []
        self.output_files = output_files or []
        self.parameters = parameters or {}
        self.started_at = started_at
        self.completed_at = completed_at
        self.metadata = metadata or {}
        
    def update_status(self, status: AnalysisStatus) -> None:
        """Update the status of the analysis.
        
        Args:
            status: New status
        """
        self.status = status
        
        # Update timestamps based on status
        now = datetime.now()
        if status == AnalysisStatus.RUNNING and not self.started_at:
            self.started_at = now
        elif status in [AnalysisStatus.SUCCEEDED, AnalysisStatus.FAILED, AnalysisStatus.CANCELED]:
            self.completed_at = now
    
    def add_output_file(self, file_info: Dict[str, Any]) -> None:
        """Add an output file to the analysis.
        
        Args:
            file_info: Information about the output file
        """
        self.output_files.append(file_info)
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the analysis.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation of the analysis
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "analysis_type": self.analysis_type,
            "sample_id": str(self.sample_id) if isinstance(self.sample_id, UUID) else self.sample_id,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "job_id": self.job_id,
            "status": self.status.value if isinstance(self.status, AnalysisStatus) else self.status,
            "input_files": self.input_files,
            "output_files": self.output_files,
            "parameters": self.parameters,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Analysis':
        """Create an Analysis from a dictionary.
        
        Args:
            data: Dictionary data
            
        Returns:
            Analysis instance
        """
        # Convert status string to enum
        if 'status' in data and isinstance(data['status'], str):
            try:
                data['status'] = AnalysisStatus(data['status'])
            except ValueError:
                # Default to pending if invalid status
                data['status'] = AnalysisStatus.PENDING
                
        # Convert timestamp strings to datetime
        if 'started_at' in data and data['started_at'] and isinstance(data['started_at'], str):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
            
        if 'completed_at' in data and data['completed_at'] and isinstance(data['completed_at'], str):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
            
        # Convert id to UUID if needed
        if 'id' in data and data['id'] and isinstance(data['id'], str):
            data['id'] = UUID(data['id'])
            
        return cls(**data)