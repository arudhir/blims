"""Container management service for BLIMS."""

from typing import List, Optional, Union
import uuid

from blims.services.sample_service import SampleService


class ContainerManager:
    """Manages container relationships between samples.
    
    This class provides functionality for adding and removing samples
    from containers, and managing the container hierarchy.
    """
    
    def __init__(self, sample_service: SampleService):
        """Initialize the container manager.
        
        Args:
            sample_service: The sample service for data persistence
        """
        self.sample_service = sample_service
    
    def add_sample_to_container(self, sample_id: Union[str, uuid.UUID], container_id: Union[str, uuid.UUID]) -> bool:
        """Add a sample to a container.
        
        Args:
            sample_id: The ID of the sample to add
            container_id: The ID of the container to add the sample to
            
        Returns:
            True if the sample was added, False otherwise
            
        Raises:
            ValueError: If the sample or container doesn't exist, or if the
                container isn't actually a container
        """
        sample = self.sample_service.get_sample(sample_id)
        container = self.sample_service.get_sample(container_id)
        
        if not sample:
            raise ValueError(f"Sample with ID {sample_id} not found")
        if not container:
            raise ValueError(f"Container with ID {container_id} not found")
        
        # Check if container is a container
        if not getattr(container, 'is_container', False):
            raise ValueError(f"Sample {container.name} is not a container")
        
        # Remove from current container if any
        if hasattr(sample, 'container_id') and sample.container_id:
            self.remove_sample_from_container(sample_id)
        
        # Add to new container
        sample.container_id = container.id
        
        # Add to container's contained_sample_ids list
        if not hasattr(container, 'contained_sample_ids'):
            container.contained_sample_ids = []
        
        if sample.id not in container.contained_sample_ids:
            container.contained_sample_ids.append(sample.id)
        
        # Update both samples
        self.sample_service.update_sample(sample)
        self.sample_service.update_sample(container)
        
        return True
    
    def remove_sample_from_container(self, sample_id: Union[str, uuid.UUID]) -> bool:
        """Remove a sample from its container.
        
        Args:
            sample_id: The ID of the sample to remove
            
        Returns:
            True if the sample was removed, False if it wasn't in a container
            
        Raises:
            ValueError: If the sample doesn't exist
        """
        sample = self.sample_service.get_sample(sample_id)
        
        if not sample:
            raise ValueError(f"Sample with ID {sample_id} not found")
        
        # Check if sample is in a container
        if not hasattr(sample, 'container_id') or not sample.container_id:
            return False
        
        # Get the container
        container = self.sample_service.get_sample(sample.container_id)
        if not container:
            # If container doesn't exist, just update the sample
            sample.container_id = None
            self.sample_service.update_sample(sample)
            return True
        
        # Remove from container's contained_sample_ids list
        if hasattr(container, 'contained_sample_ids'):
            if sample.id in container.contained_sample_ids:
                container.contained_sample_ids.remove(sample.id)
                self.sample_service.update_sample(container)
        
        # Update sample
        sample.container_id = None
        self.sample_service.update_sample(sample)
        
        return True
    
    def get_container_hierarchy(self, container_id: Union[str, uuid.UUID]) -> List[dict]:
        """Get the hierarchy of a container, including all contained samples.
        
        Args:
            container_id: The ID of the container
            
        Returns:
            A nested list representing the container hierarchy
            
        Raises:
            ValueError: If the container doesn't exist
        """
        container = self.sample_service.get_sample(container_id)
        
        if not container:
            raise ValueError(f"Container with ID {container_id} not found")
        
        # Check if container is a container
        if not getattr(container, 'is_container', False):
            raise ValueError(f"Sample {container.name} is not a container")
        
        # Build hierarchy recursively
        return self._build_hierarchy(container)
    
    def _build_hierarchy(self, container) -> dict:
        """Build a hierarchy dictionary for a container.
        
        Args:
            container: The container to build the hierarchy for
            
        Returns:
            A dictionary representing the container and its contained samples
        """
        result = {
            'id': str(container.id),
            'name': container.name,
            'type': container.sample_type,
            'children': []
        }
        
        if hasattr(container, 'contained_sample_ids') and container.contained_sample_ids:
            for sample_id in container.contained_sample_ids:
                sample = self.sample_service.get_sample(sample_id)
                if sample:
                    if getattr(sample, 'is_container', False):
                        # Recursive call for nested containers
                        result['children'].append(self._build_hierarchy(sample))
                    else:
                        # Add leaf sample
                        result['children'].append({
                            'id': str(sample.id),
                            'name': sample.name,
                            'type': sample.sample_type,
                        })
        
        return result