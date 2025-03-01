"""Sample model for BLIMS."""
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4, UUID


class Sample:
    """A sample in the LIMS system.
    
    Samples can have metadata, associated files, and lineage relationships.
    """
    
    def __init__(
        self,
        name: str,
        sample_type: str,
        created_by: str,
        id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_ids: Optional[List[UUID]] = None,
        file_paths: Optional[List[str]] = None,
    ):
        """Initialize a new Sample.
        
        Args:
            name: The name of the sample
            sample_type: The type of sample (e.g., blood, tissue, extract)
            created_by: The user who created this sample
            id: Unique identifier (generated if not provided)
            metadata: Additional sample metadata as key-value pairs
            parent_ids: IDs of samples this sample was derived from
            file_paths: Paths to files associated with this sample
        """
        self.id = id or uuid4()
        self.name = name
        self.sample_type = sample_type
        self.created_by = created_by
        self.created_at = datetime.now()
        self.metadata = metadata or {}
        self.parent_ids = parent_ids or []
        self.file_paths = file_paths or []
        self.child_ids: List[UUID] = []
        
    def add_metadata(self, key: str, value: Any) -> None:
        """Add or update metadata for this sample.
        
        Args:
            key: The metadata field name
            value: The metadata value
        """
        self.metadata[key] = value
        
    def add_file(self, file_path: str) -> None:
        """Add a file to this sample.
        
        Args:
            file_path: Path to the file
        """
        if file_path not in self.file_paths:
            self.file_paths.append(file_path)
            
    def add_parent(self, parent_id: UUID) -> None:
        """Add a parent sample to this sample's lineage.
        
        Args:
            parent_id: The ID of the parent sample
        """
        if parent_id not in self.parent_ids:
            self.parent_ids.append(parent_id)
            
    def add_child(self, child_id: UUID) -> None:
        """Add a child sample to this sample's lineage.
        
        Args:
            child_id: The ID of the child sample
        """
        if child_id not in self.child_ids:
            self.child_ids.append(child_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert this sample to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the sample
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "sample_type": self.sample_type,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "parent_ids": [str(pid) for pid in self.parent_ids],
            "child_ids": [str(cid) for cid in self.child_ids],
            "file_paths": self.file_paths
        }