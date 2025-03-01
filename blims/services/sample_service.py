"""Service for managing samples in BLIMS."""

from typing import Dict, List, Optional, Union
import uuid
from datetime import datetime

from blims.models.sample import Sample


class SampleService:
    """Service for managing samples in the LIMS system.
    
    This service provides business logic for creating, updating,
    and querying samples.
    """
    
    def __init__(self, sample_repository):
        """Initialize the sample service.
        
        Args:
            sample_repository: Repository for sample persistence
        """
        self.sample_repository = sample_repository
    
    def create_sample(self, sample: Sample) -> Sample:
        """Create a new sample.
        
        Args:
            sample: The sample to create
            
        Returns:
            The created sample
        """
        return self.sample_repository.create_sample(sample)
    
    def get_sample(self, sample_id: Union[str, uuid.UUID]) -> Optional[Sample]:
        """Get a sample by ID.
        
        Args:
            sample_id: The ID of the sample to retrieve
            
        Returns:
            The sample if found, None otherwise
        """
        return self.sample_repository.get_sample(sample_id)
    
    def get_sample_by_sample_id(self, sample_id: str) -> Optional[Sample]:
        """Get a sample by its human-readable sample ID.
        
        Args:
            sample_id: The sample_id of the sample to retrieve
            
        Returns:
            The sample if found, None otherwise
        """
        return self.sample_repository.get_sample_by_sample_id(sample_id)
    
    def get_all_samples(self) -> List[Sample]:
        """Get all samples.
        
        Returns:
            List of all samples
        """
        return self.sample_repository.get_all_samples()
    
    def update_sample(self, sample: Sample) -> Sample:
        """Update an existing sample.
        
        Args:
            sample: The sample with updated fields
            
        Returns:
            The updated sample
            
        Raises:
            ValueError: If the sample doesn't exist
        """
        return self.sample_repository.update_sample(sample)
    
    def delete_sample(self, sample_id: Union[str, uuid.UUID]) -> bool:
        """Delete a sample.
        
        Args:
            sample_id: The ID of the sample to delete
            
        Returns:
            True if the sample was deleted, False if it didn't exist
        """
        return self.sample_repository.delete_sample(sample_id)
    
    def get_samples_by_type(self, sample_type: str) -> List[Sample]:
        """Get all samples of a specific type.
        
        Args:
            sample_type: The sample type to filter by
            
        Returns:
            List of samples with the specified type
        """
        return self.sample_repository.get_samples_by_type(sample_type)
    
    def get_samples_by_container(self, container_id: Union[str, uuid.UUID]) -> List[Sample]:
        """Get all samples in a specific container.
        
        Args:
            container_id: The ID of the container
            
        Returns:
            List of samples in the container
        """
        return self.sample_repository.get_samples_by_container(container_id)
    
    def get_containers(self) -> List[Sample]:
        """Get all containers.
        
        Returns:
            List of all containers (samples that are containers)
        """
        return self.sample_repository.get_containers()