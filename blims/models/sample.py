"""Sample model for BLIMS."""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

# Global counter for sample IDs
_next_sample_number = 1


def get_next_sample_id() -> str:
    """Get the next sample ID in the format 's1', 's2', etc.
    
    Returns:
        A string with the next sample ID
    """
    global _next_sample_number
    sample_id = f"s{_next_sample_number}"
    _next_sample_number += 1
    return sample_id


def reset_sample_counter(max_id: int = 0):
    """Reset the sample counter to start after the given max ID.
    
    Args:
        max_id: The maximum ID currently in use
    """
    global _next_sample_number
    _next_sample_number = max_id + 1


def extract_sample_number(sample_id: str) -> int:
    """Extract the number from a sample ID (e.g., 's1' -> 1).
    
    Args:
        sample_id: The sample ID string
        
    Returns:
        The extracted number
    """
    if not sample_id or not isinstance(sample_id, str):
        return 0
        
    match = re.match(r's(\d+)', sample_id)
    if match:
        return int(match.group(1))
    return 0


class Sample:
    """A sample in the LIMS system.

    Samples can have metadata, associated files, and lineage relationships.
    They can also contain other samples or be containers themselves.
    """

    def __init__(
        self,
        name: str,
        sample_type: str,
        created_by: str,
        id: Optional[Union[UUID, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_ids: Optional[List[Union[UUID, str]]] = None,
        file_paths: Optional[List[str]] = None,
        contained_sample_ids: Optional[List[Union[UUID, str]]] = None,
        sample_id: Optional[str] = None,
        barcode: Optional[str] = None,
        is_container: bool = False,
        sequencing_data: Optional[List[Dict[str, Any]]] = None,
        analyses: Optional[List[Dict[str, Any]]] = None,
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
            contained_sample_ids: IDs of samples contained within this sample
            sample_id: Human-readable ID (s1, s2, etc.) generated if not provided
            barcode: Optional barcode identifier for the sample
            is_container: Whether this sample is a container
        """
        self.id = id or uuid4()
        self.sample_id = sample_id or get_next_sample_id()
        self.name = name
        self.sample_type = sample_type
        self.created_by = created_by
        self.created_at = datetime.now()
        self.metadata = metadata or {}
        self.parent_ids = parent_ids or []
        self.file_paths = file_paths or []
        self.child_ids: List[Union[UUID, str]] = []
        self.contained_sample_ids = contained_sample_ids or []
        self.container_id: Optional[Union[UUID, str]] = None  # ID of the sample containing this one
        self.barcode = barcode
        self.is_container = is_container
        self.sequencing_data = sequencing_data or []
        self.analyses = analyses or []

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
            
    def add_contained_sample(self, sample_id: UUID) -> None:
        """Add a sample to be contained within this sample.
        
        Args:
            sample_id: The ID of the sample to contain
        """
        if sample_id not in self.contained_sample_ids:
            self.contained_sample_ids.append(sample_id)
            
    def remove_contained_sample(self, sample_id: UUID) -> None:
        """Remove a contained sample from this sample.
        
        Args:
            sample_id: The ID of the sample to remove
        """
        if sample_id in self.contained_sample_ids:
            self.contained_sample_ids.remove(sample_id)
            
    def set_container(self, container_id: Optional[UUID]) -> None:
        """Set the container of this sample.
        
        Args:
            container_id: The ID of the container sample, or None to remove
        """
        self.container_id = container_id

    def add_sequencing_data(self, data: Dict[str, Any]) -> None:
        """Add sequencing data reference to this sample.
        
        Args:
            data: Dictionary with sequencing data information
        """
        self.sequencing_data.append(data)
    
    def add_analysis(self, analysis: Dict[str, Any]) -> None:
        """Add analysis reference to this sample.
        
        Args:
            analysis: Dictionary with analysis information
        """
        self.analyses.append(analysis)
        
    def get_sequencing_data(self, data_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get sequencing data for this sample.
        
        Args:
            data_type: Optional type of sequencing data to filter by
            
        Returns:
            List of sequencing data dictionaries
        """
        if not data_type:
            return self.sequencing_data
        
        return [data for data in self.sequencing_data if data.get('type') == data_type]
    
    def get_analyses(self, analysis_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get analyses for this sample.
        
        Args:
            analysis_type: Optional type of analysis to filter by
            
        Returns:
            List of analysis dictionaries
        """
        if not analysis_type:
            return self.analyses
        
        return [analysis for analysis in self.analyses if analysis.get('type') == analysis_type]

    def to_dict(self) -> Dict[str, Any]:
        """Convert this sample to a dictionary for serialization.

        Returns:
            Dictionary representation of the sample
        """
        return {
            "id": str(self.id),
            "sample_id": self.sample_id,
            "name": self.name,
            "sample_type": self.sample_type,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "parent_ids": [str(pid) for pid in self.parent_ids],
            "child_ids": [str(cid) for cid in self.child_ids],
            "file_paths": self.file_paths,
            "contained_sample_ids": [str(sid) for sid in self.contained_sample_ids],
            "container_id": str(self.container_id) if self.container_id else None,
            "barcode": self.barcode,
            "is_container": self.is_container,
            "sequencing_data": self.sequencing_data,
            "analyses": self.analyses,
        }
