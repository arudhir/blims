"""Sample service for handling LIMS operations."""
from typing import Dict, List, Any, Optional
from uuid import UUID

from blims.models.sample import Sample
from blims.core.repository import SampleRepository


class SampleService:
    """Service for managing sample operations.
    
    This class implements business logic for sample operations in the LIMS.
    """
    
    def __init__(self, repository: Optional[SampleRepository] = None):
        """Initialize a new sample service.
        
        Args:
            repository: The repository to use for storage (creates new if None)
        """
        self.repository = repository or SampleRepository()
        
    def create_sample(
        self,
        name: str,
        sample_type: str,
        created_by: str,
        metadata: Optional[Dict[str, Any]] = None,
        parent_ids: Optional[List[UUID]] = None,
        file_paths: Optional[List[str]] = None,
    ) -> Sample:
        """Create a new sample.
        
        Args:
            name: The name of the sample
            sample_type: The type of sample
            created_by: The user creating the sample
            metadata: Additional sample metadata
            parent_ids: IDs of samples this sample was derived from
            file_paths: Paths to files associated with this sample
            
        Returns:
            The newly created sample
            
        Raises:
            ValueError: If parent samples don't exist
        """
        # Validate parent samples exist
        if parent_ids:
            for parent_id in parent_ids:
                if not self.repository.get(parent_id):
                    raise ValueError(f"Parent sample with ID {parent_id} not found")
        
        # Create and add the sample
        sample = Sample(
            name=name,
            sample_type=sample_type,
            created_by=created_by,
            metadata=metadata,
            parent_ids=parent_ids,
            file_paths=file_paths,
        )
        
        self.repository.add(sample)
        return sample
    
    def derive_sample(
        self,
        parent_id: UUID,
        name: str,
        sample_type: str,
        created_by: str,
        metadata: Optional[Dict[str, Any]] = None,
        file_paths: Optional[List[str]] = None,
    ) -> Sample:
        """Create a new sample derived from an existing sample.
        
        Args:
            parent_id: The ID of the parent sample
            name: The name of the derived sample
            sample_type: The type of derived sample
            created_by: The user creating the sample
            metadata: Additional sample metadata
            file_paths: Paths to files associated with this sample
            
        Returns:
            The newly created derived sample
            
        Raises:
            ValueError: If the parent sample doesn't exist
        """
        parent = self.repository.get(parent_id)
        if not parent:
            raise ValueError(f"Parent sample with ID {parent_id} not found")
        
        return self.create_sample(
            name=name,
            sample_type=sample_type,
            created_by=created_by,
            metadata=metadata,
            parent_ids=[parent_id],
            file_paths=file_paths,
        )
    
    def add_metadata_to_sample(self, sample_id: UUID, key: str, value: Any) -> Sample:
        """Add metadata to an existing sample.
        
        Args:
            sample_id: The ID of the sample to modify
            key: The metadata key
            value: The metadata value
            
        Returns:
            The updated sample
            
        Raises:
            ValueError: If the sample doesn't exist
        """
        sample = self.repository.get(sample_id)
        if not sample:
            raise ValueError(f"Sample with ID {sample_id} not found")
        
        sample.add_metadata(key, value)
        return sample
    
    def add_file_to_sample(self, sample_id: UUID, file_path: str) -> Sample:
        """Add a file to an existing sample.
        
        Args:
            sample_id: The ID of the sample to modify
            file_path: The path to the file
            
        Returns:
            The updated sample
            
        Raises:
            ValueError: If the sample doesn't exist
        """
        sample = self.repository.get(sample_id)
        if not sample:
            raise ValueError(f"Sample with ID {sample_id} not found")
        
        sample.add_file(file_path)
        return sample
    
    def get_sample_lineage(self, sample_id: UUID) -> Dict[str, List[Sample]]:
        """Get the complete lineage of a sample (parents and children).
        
        Args:
            sample_id: The ID of the sample to get lineage for
            
        Returns:
            Dictionary with "ancestors" and "descendants" lists
            
        Raises:
            ValueError: If the sample doesn't exist
        """
        sample = self.repository.get(sample_id)
        if not sample:
            raise ValueError(f"Sample with ID {sample_id} not found")
        
        return {
            "ancestors": self.repository.get_ancestry(sample_id),
            "descendants": self.repository.get_descendants(sample_id),
        }
    
    def search_samples(self, metadata_filters: Dict[str, Any]) -> List[Sample]:
        """Search for samples matching metadata filters.
        
        Args:
            metadata_filters: Dictionary of metadata key-value pairs to match
            
        Returns:
            List of samples matching all filters
        """
        # Start with all samples
        results = self.repository.get_all()
        
        # Apply each filter
        for key, value in metadata_filters.items():
            results = [
                sample for sample in results
                if key in sample.metadata and sample.metadata[key] == value
            ]
            
        return results