"""Repository for managing samples."""

from typing import Dict, List, Optional, Union
import uuid

from blims.models.sample import Sample


class SampleRepository:
    """Repository for managing samples.
    
    This repository handles the storage and retrieval of Sample objects, with
    methods for creating, updating, and querying samples.
    """
    
    def __init__(self):
        """Initialize the sample repository."""
        self.samples: Dict[str, Sample] = {}
        self.sample_ids: Dict[str, str] = {}  # Maps sample_id to sample UUID
    
    def create_sample(self, sample: Sample) -> Sample:
        """Store a new sample in the repository.
        
        Args:
            sample: The sample to store
            
        Returns:
            The stored sample with any repository-assigned fields
        """
        sample_id = str(sample.id)
        self.samples[sample_id] = sample
        
        # Create a mapping for sample_id if it exists
        if hasattr(sample, 'sample_id') and sample.sample_id:
            self.sample_ids[sample.sample_id] = sample_id
        
        return sample
    
    def get_sample(self, sample_id: Union[str, uuid.UUID]) -> Optional[Sample]:
        """Retrieve a sample by its ID.
        
        Args:
            sample_id: The ID of the sample to retrieve
            
        Returns:
            The sample if found, None otherwise
        """
        sample_id_str = str(sample_id)
        return self.samples.get(sample_id_str)
    
    def get_sample_by_sample_id(self, sample_id: str) -> Optional[Sample]:
        """Retrieve a sample by its human-readable sample ID.
        
        Args:
            sample_id: The sample_id of the sample to retrieve
            
        Returns:
            The sample if found, None otherwise
        """
        if sample_id in self.sample_ids:
            return self.samples.get(self.sample_ids[sample_id])
        
        # Fallback: iterate through samples to find matching sample_id
        for sample in self.samples.values():
            if hasattr(sample, 'sample_id') and sample.sample_id == sample_id:
                # Update the mapping for future lookups
                self.sample_ids[sample_id] = str(sample.id)
                return sample
        
        return None
    
    def update_sample(self, sample: Sample) -> Sample:
        """Update an existing sample.
        
        Args:
            sample: The sample with updated fields
            
        Returns:
            The updated sample
            
        Raises:
            ValueError: If the sample doesn't exist
        """
        sample_id = str(sample.id)
        if sample_id not in self.samples:
            raise ValueError(f"Sample with ID {sample_id} not found")
        
        # Update the mapping if sample_id has changed
        old_sample = self.samples[sample_id]
        if hasattr(old_sample, 'sample_id') and hasattr(sample, 'sample_id'):
            if old_sample.sample_id != sample.sample_id:
                if old_sample.sample_id in self.sample_ids:
                    del self.sample_ids[old_sample.sample_id]
                if sample.sample_id:
                    self.sample_ids[sample.sample_id] = sample_id
        
        self.samples[sample_id] = sample
        return sample
    
    def delete_sample(self, sample_id: Union[str, uuid.UUID]) -> bool:
        """Delete a sample from the repository.
        
        Args:
            sample_id: The ID of the sample to delete
            
        Returns:
            True if the sample was deleted, False if it didn't exist
        """
        sample_id_str = str(sample_id)
        if sample_id_str in self.samples:
            # Remove from sample_ids mapping if needed
            sample = self.samples[sample_id_str]
            if hasattr(sample, 'sample_id') and sample.sample_id in self.sample_ids:
                del self.sample_ids[sample.sample_id]
            
            del self.samples[sample_id_str]
            return True
        return False
    
    def get_all_samples(self) -> List[Sample]:
        """Get all samples in the repository.
        
        Returns:
            List of all samples
        """
        return list(self.samples.values())
    
    def get_samples_by_type(self, sample_type: str) -> List[Sample]:
        """Get all samples of a specific type.
        
        Args:
            sample_type: The sample type to filter by
            
        Returns:
            List of samples with the specified type
        """
        return [s for s in self.samples.values() if s.sample_type == sample_type]
    
    def get_samples_by_container(self, container_id: Union[str, uuid.UUID]) -> List[Sample]:
        """Get all samples in a specific container.
        
        Args:
            container_id: The ID of the container
            
        Returns:
            List of samples in the container
        """
        container_id_str = str(container_id)
        return [s for s in self.samples.values() if hasattr(s, 'container_id') and str(s.container_id) == container_id_str]
    
    def get_containers(self) -> List[Sample]:
        """Get all containers.
        
        Returns:
            List of all containers (samples that are containers)
        """
        return [s for s in self.samples.values() if hasattr(s, 'is_container') and s.is_container]