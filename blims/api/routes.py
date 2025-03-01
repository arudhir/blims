"""API routes for the BLIMS system."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from blims.core.service import SampleService

# Create a router
router = APIRouter(prefix="/api/v1")


# Service dependency
def get_sample_service():
    """Dependency for getting the sample service."""
    return SampleService()


# Request models
class SampleCreate(BaseModel):
    name: str
    sample_type: str
    created_by: str
    metadata: Optional[Dict[str, Any]] = None
    parent_ids: Optional[List[str]] = None
    file_paths: Optional[List[str]] = None


class SampleDerive(BaseModel):
    name: str
    sample_type: str
    created_by: str
    metadata: Optional[Dict[str, Any]] = None
    file_paths: Optional[List[str]] = None


class MetadataAdd(BaseModel):
    key: str
    value: Any


class FileAdd(BaseModel):
    file_path: str


@router.post("/samples", response_model=Dict[str, Any])
def create_sample(
    sample: SampleCreate,
    service: SampleService = Depends(get_sample_service),
):
    """Create a new sample.

    Args:
        sample: The sample information

    Returns:
        The created sample data
    """
    try:
        # Convert string UUIDs to UUID objects
        uuid_parent_ids = None
        if sample.parent_ids:
            uuid_parent_ids = [UUID(pid) for pid in sample.parent_ids]

        created_sample = service.create_sample(
            name=sample.name,
            sample_type=sample.sample_type,
            created_by=sample.created_by,
            metadata=sample.metadata,
            parent_ids=uuid_parent_ids,
            file_paths=sample.file_paths,
        )
        return created_sample.to_dict()
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
            raise HTTPException(
                status_code=404, detail=f"Sample with ID {sample_id} not found"
            )
        return sample.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/samples/{sample_id}/metadata", response_model=Dict[str, Any])
def add_metadata(
    sample_id: str,
    metadata: MetadataAdd,
    service: SampleService = Depends(get_sample_service),
):
    """Add metadata to a sample.

    Args:
        sample_id: The ID of the sample to modify
        metadata: The metadata key and value

    Returns:
        The updated sample data

    Raises:
        HTTPException: If the sample is not found
    """
    try:
        uuid_id = UUID(sample_id)
        sample = service.add_metadata_to_sample(uuid_id, metadata.key, metadata.value)
        return sample.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/samples/{sample_id}/files", response_model=Dict[str, Any])
def add_file(
    sample_id: str,
    file_data: FileAdd,
    service: SampleService = Depends(get_sample_service),
):
    """Add a file to a sample.

    Args:
        sample_id: The ID of the sample to modify
        file_data: Contains path to the file

    Returns:
        The updated sample data

    Raises:
        HTTPException: If the sample is not found
    """
    try:
        uuid_id = UUID(sample_id)
        sample = service.add_file_to_sample(uuid_id, file_data.file_path)
        return sample.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/samples/{parent_id}/derive", response_model=Dict[str, Any])
def derive_sample(
    parent_id: str,
    sample: SampleDerive,
    service: SampleService = Depends(get_sample_service),
):
    """Create a new sample derived from an existing sample.

    Args:
        parent_id: The ID of the parent sample
        sample: Information for the derived sample

    Returns:
        The created sample data

    Raises:
        HTTPException: If the parent sample is not found
    """
    try:
        uuid_parent_id = UUID(parent_id)
        derived_sample = service.derive_sample(
            parent_id=uuid_parent_id,
            name=sample.name,
            sample_type=sample.sample_type,
            created_by=sample.created_by,
            metadata=sample.metadata,
            file_paths=sample.file_paths,
        )
        return derived_sample.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/samples/{sample_id}/lineage", response_model=Dict[str, List[Dict[str, Any]]]
)
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


class SearchMetadata(BaseModel):
    search_test: Optional[bool] = None
    group: Optional[str] = None


@router.get("/samples", response_model=List[Dict[str, Any]])
def search_samples(
    search_test: Optional[bool] = None,
    group: Optional[str] = None,
    service: SampleService = Depends(get_sample_service),
):
    """Search for samples based on metadata filters.

    Args:
        search_test: Optional boolean to filter by search_test metadata
        group: Optional string to filter by group metadata

    Returns:
        List of matching samples
    """
    # Build metadata filters from query parameters
    metadata_dict = {}
    if search_test is not None:
        metadata_dict["search_test"] = search_test
    if group is not None:
        metadata_dict["group"] = group

    # If no filters provided, return all samples
    if not metadata_dict:
        return [sample.to_dict() for sample in service.repository.get_all()]

    # Search with filters
    results = service.search_samples(metadata_dict)
    return [sample.to_dict() for sample in results]
