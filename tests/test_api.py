"""Tests for the API routes."""
from fastapi.testclient import TestClient
import pytest
from uuid import UUID, uuid4

from blims.models.sample import Sample
from blims.core.repository import SampleRepository
from blims.core.service import SampleService
from blims.api.routes import get_sample_service
import main
from main import app

# Set up a test client with a consistent repository
test_repo = SampleRepository()
test_service = SampleService(repository=test_repo)

# Add a test fixture to ensure we always start with a clean repository
@pytest.fixture(autouse=True)
def reset_test_repo():
    test_repo._samples = {}

# Override the service dependency
def get_test_service_override():
    return test_service

# Override the dependency in the app
app.dependency_overrides[get_sample_service] = get_test_service_override

# Create the test client
client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "name" in response.json()
    assert "version" in response.json()
    assert "description" in response.json()


def create_test_sample():
    """Helper function to create a test sample and return its ID."""
    sample_data = {
        "name": "API Test Sample",
        "sample_type": "Blood",
        "created_by": "API Tester",
        "metadata": {"source": "api_test"}
    }
    
    response = client.post("/api/v1/samples", json=sample_data)
    if response.status_code != 200:
        return None
        
    result = response.json()
    return result["id"] if "id" in result else None

def test_create_sample():
    """Test creating a sample via API."""
    sample_data = {
        "name": "API Test Sample",
        "sample_type": "Blood",
        "created_by": "API Tester",
        "metadata": {"source": "api_test"}
    }
    
    response = client.post("/api/v1/samples", json=sample_data)
    assert response.status_code == 200
    
    result = response.json()
    assert result["name"] == sample_data["name"]
    assert result["sample_type"] == sample_data["sample_type"]
    assert result["created_by"] == sample_data["created_by"]
    assert result["metadata"] == sample_data["metadata"]
    assert "id" in result
    
    # Verify we can get the sample from our test repository
    sample_id = UUID(result["id"])
    assert test_repo.get(sample_id) is not None


def test_get_sample():
    """Test retrieving a sample via API."""
    # First create a sample
    sample_id = create_test_sample()
    assert sample_id is not None
    
    # Then retrieve it
    response = client.get(f"/api/v1/samples/{sample_id}")
    assert response.status_code == 200
    
    result = response.json()
    assert result["id"] == sample_id
    assert result["name"] == "API Test Sample"


def test_get_nonexistent_sample():
    """Test retrieving a non-existent sample."""
    response = client.get("/api/v1/samples/00000000-0000-0000-0000-000000000999")
    assert response.status_code == 404


def test_add_metadata_to_sample():
    """Test adding metadata to a sample via API."""
    # First create a sample
    sample_id = create_test_sample()
    assert sample_id is not None
    
    # Then add metadata
    metadata_data = {
        "key": "test_key",
        "value": "test_value"
    }
    
    response = client.post(f"/api/v1/samples/{sample_id}/metadata", json=metadata_data)
    assert response.status_code == 200
    
    result = response.json()
    assert result["metadata"]["test_key"] == "test_value"


def test_add_metadata_to_nonexistent_sample():
    """Test adding metadata to a non-existent sample."""
    metadata_data = {
        "key": "test_key",
        "value": "test_value"
    }
    
    response = client.post(
        "/api/v1/samples/00000000-0000-0000-0000-000000000999/metadata", 
        json=metadata_data
    )
    assert response.status_code in [404, 400]  # Either not found or invalid UUID


def test_add_file_to_sample():
    """Test adding a file to a sample via API."""
    # First create a sample
    sample_id = create_test_sample()
    assert sample_id is not None
    
    # Then add file
    file_data = {
        "file_path": "/path/to/test_file.txt"
    }
    
    response = client.post(f"/api/v1/samples/{sample_id}/files", json=file_data)
    assert response.status_code == 200
    
    result = response.json()
    assert "/path/to/test_file.txt" in result["file_paths"]


def test_derive_sample():
    """Test deriving a sample via API."""
    # First create a parent sample
    parent_id = create_test_sample()
    assert parent_id is not None
    
    # Then derive a sample
    derived_data = {
        "name": "Derived Sample",
        "sample_type": "DNA Extract",
        "created_by": "API Tester",
        "metadata": {"derived": True}
    }
    
    response = client.post(f"/api/v1/samples/{parent_id}/derive", json=derived_data)
    assert response.status_code == 200
    
    result = response.json()
    assert result["name"] == derived_data["name"]
    assert parent_id in result["parent_ids"]
    assert result["metadata"] == derived_data["metadata"]


def test_get_lineage():
    """Test getting a sample's lineage via API."""
    # First create a parent sample
    parent_id = create_test_sample()
    assert parent_id is not None
    
    # Then derive a sample
    derived_data = {
        "name": "Lineage Test Child",
        "sample_type": "DNA Extract",
        "created_by": "API Tester"
    }
    
    derive_response = client.post(f"/api/v1/samples/{parent_id}/derive", json=derived_data)
    assert derive_response.status_code == 200
    
    child_id = derive_response.json()["id"]
    
    # Get parent's lineage
    response = client.get(f"/api/v1/samples/{parent_id}/lineage")
    assert response.status_code == 200
    
    lineage = response.json()
    assert len(lineage["ancestors"]) == 0
    assert len(lineage["descendants"]) == 1
    assert lineage["descendants"][0]["id"] == child_id
    
    # Get child's lineage
    response = client.get(f"/api/v1/samples/{child_id}/lineage")
    assert response.status_code == 200
    
    lineage = response.json()
    assert len(lineage["ancestors"]) == 1
    assert lineage["ancestors"][0]["id"] == parent_id
    assert len(lineage["descendants"]) == 0


def test_search_samples():
    """Test searching for samples via API."""
    # Create samples with different metadata
    sample_data_1 = {
        "name": "Search Test A",
        "sample_type": "Blood",
        "created_by": "API Tester",
        "metadata": {"search_test": True, "group": "A"}
    }
    
    sample_data_2 = {
        "name": "Search Test B",
        "sample_type": "Blood",
        "created_by": "API Tester",
        "metadata": {"search_test": True, "group": "B"}
    }
    
    # Clear repository first to have predictable results
    test_repo._samples = {}
    
    # Create test samples
    response1 = client.post("/api/v1/samples", json=sample_data_1)
    response2 = client.post("/api/v1/samples", json=sample_data_2)
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Search by using search_test query parameter
    response = client.get("/api/v1/samples", params={"search_test": True})
    assert response.status_code == 200
    
    results = response.json()
    assert len(results) == 2
    
    # Verify both our test samples are in the results
    sample_names = [s["name"] for s in results]
    assert "Search Test A" in sample_names
    assert "Search Test B" in sample_names
    
    # Test search by group
    response = client.get("/api/v1/samples", params={"group": "A"})
    assert response.status_code == 200
    
    results = response.json()
    assert len(results) == 1
    assert results[0]["name"] == "Search Test A"