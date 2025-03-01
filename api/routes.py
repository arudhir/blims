"""API routes for the BLIMS system."""
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends

from blims.models.sample import Sample
from blims.core.service import SampleService


# Create a router
router = APIRouter(prefix="/api/v1")

# Service dependency
def get_sample_service():
    """Dependency for getting the sample service."""
    return SampleService()


# Sample API Routes
@router.post("/samples", response_model=Dict[str, Any])
def create_sample(
    name: str,
    sample_type: str,
    created_by: str,
    metadata: Optional[Dict[str, Any]] = None,
    parent_ids: Optional[List[str]] = None,
    file_paths: Optional[List[str]] = None,
    service: SampleService = Depends(get_sample_service),
):
    """Create a new sample.
    
    Args:
        name: The name of the sample
        sample_type: The type of sample
        created_by: The user creating the sample
        metadata: Optional metadata as key-value pairs
        parent_ids: Optional IDs of parent samples
        file_paths: Optional file paths to associate with the sample
        
    Returns:
        The created sample data
    """
    try:
        # Convert string UUIDs to UUID objects
        uuid_parent_ids = None
        if parent_ids:
            uuid_parent_ids = [UUID(pid) for pid in parent_ids]
            
        sample = service.create_sample(
            name=name,
            sample_type=sample_type,
            created_by=created_by,
            metadata=metadata,
            parent_ids=uuid_parent_ids,
            file_paths=file_paths,
        )
        return sample.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/samples/{sample_id}", response_model=Dict[str, Any])
def get_sample(
    sample_id: str,
    service: SampleService = Depends(get_sample_service),
):
    """Get a sample by ID.
    
    Args:
        sample_id: The ID of the sample to retrieve
        
    Returns:
        The sample data
        
    Raises:
        HTTPException: If the sample is not found
    """
    try:
        uuid_id = UUID(sample_id)
        sample = service.repository.get(uuid_id)
        if not sample:
            raise HTTPException(status_code=404, detail=f"Sample with ID {sample_id} not found")
        return sample.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/samples/{sample_id}/metadata", response_model=Dict[str, Any])
def add_metadata(
    sample_id: str,
    key: str,
    value: Any,
    service: SampleService = Depends(get_sample_service),
):
    """Add metadata to a sample.
    
    Args:
        sample_id: The ID of the sample to modify
        key: The metadata key
        value: The metadata value
        
    Returns:
        The updated sample data
        
    Raises:
        HTTPException: If the sample is not found
    """
    try:
        uuid_id = UUID(sample_id)
        sample = service.add_metadata_to_sample(uuid_id, key, value)
        return sample.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/samples/{sample_id}/files", response_model=Dict[str, Any])
def add_file(
    sample_id: str,
    file_path: str,
    service: SampleService = Depends(get_sample_service),
):
    """Add a file to a sample.
    
    Args:
        sample_id: The ID of the sample to modify
        file_path: Path to the file
        
    Returns:
        The updated sample data
        
    Raises:
        HTTPException: If the sample is not found
    """
    try:
        uuid_id = UUID(sample_id)
        sample = service.add_file_to_sample(uuid_id, file_path)
        return sample.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/samples/{parent_id}/derive", response_model=Dict[str, Any])
def derive_sample(
    parent_id: str,
    name: str,
    sample_type: str,
    created_by: str,
    metadata: Optional[Dict[str, Any]] = None,
    file_paths: Optional[List[str]] = None,
    service: SampleService = Depends(get_sample_service),
):
    """Create a new sample derived from an existing sample.
    
    Args:
        parent_id: The ID of the parent sample
        name: The name of the derived sample
        sample_type: The type of derived sample
        created_by: The user creating the sample
        metadata: Optional metadata as key-value pairs
        file_paths: Optional file paths to associate with the sample
        
    Returns:
        The created sample data
        
    Raises:
        HTTPException: If the parent sample is not found
    """
    try:
        uuid_parent_id = UUID(parent_id)
        sample = service.derive_sample(
            parent_id=uuid_parent_id,
            name=name,
            sample_type=sample_type,
            created_by=created_by,
            metadata=metadata,
            file_paths=file_paths,
        )
        return sample.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/samples/{sample_id}/lineage", response_model=Dict[str, List[Dict[str, Any]]])
def get_lineage(
    sample_id: str,
    service: SampleService = Depends(get_sample_service),
):
    """Get the complete lineage of a sample.
    
    Args:
        sample_id: The ID of the sample
        
    Returns:
        Dictionary with ancestors and descendants
        
    Raises:
        HTTPException: If the sample is not found
    """
    try:
        uuid_id = UUID(sample_id)
        lineage = service.get_sample_lineage(uuid_id)
        
        # Convert samples to dictionaries
        return {
            "ancestors": [sample.to_dict() for sample in lineage["ancestors"]],
            "descendants": [sample.to_dict() for sample in lineage["descendants"]],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/samples", response_model=List[Dict[str, Any]])
def search_samples(
    metadata: Optional[Dict[str, Any]] = None,
    service: SampleService = Depends(get_sample_service),
):
    """Search for samples based on metadata filters.
    
    Args:
        metadata: Key-value pairs to filter samples by
        
    Returns:
        List of matching samples
    """
    # If no filters provided, return all samples
    if not metadata:
        return [sample.to_dict() for sample in service.repository.get_all()]
    
    # Search with filters
    results = service.search_samples(metadata)
    return [sample.to_dict() for sample in results]