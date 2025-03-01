"""Test configuration and fixtures."""
import pytest
from uuid import UUID, uuid4

from blims.core.repository import SampleRepository
from blims.core.service import SampleService
from blims.models.sample import Sample


@pytest.fixture(scope="session")
def sample_repository():
    """Create a repository for testing."""
    return SampleRepository()


@pytest.fixture(scope="session")
def sample_service(sample_repository):
    """Create a service with the test repository."""
    return SampleService(repository=sample_repository)


@pytest.fixture
def clear_repository(sample_repository):
    """Clear the repository before each test."""
    sample_repository._samples = {}