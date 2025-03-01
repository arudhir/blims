"""Test configuration and fixtures."""
import pytest
from uuid import UUID, uuid4

# Import repositories
from blims.repositories.sample_repository import SampleRepository
from blims.repositories.genome_repository import GenomeRepository
from blims.repositories.feature_repository import FeatureRepository
from blims.repositories.job_repository import JobRepository

# Import services
from blims.services.sample_service import SampleService
from blims.services.genome_service import GenomeService
from blims.services.job_service import JobService

# Import models
from blims.models.sample import Sample
from blims.models.genome import Genome
from blims.models.feature import Feature, FeatureType
from blims.models.job import Job, JobStatus, JobType


@pytest.fixture(scope="session")
def sample_repository():
    """Create a sample repository for testing."""
    return SampleRepository()


@pytest.fixture(scope="session")
def genome_repository():
    """Create a genome repository for testing."""
    return GenomeRepository()


@pytest.fixture(scope="session")
def feature_repository():
    """Create a feature repository for testing."""
    return FeatureRepository()


@pytest.fixture(scope="session")
def job_repository():
    """Create a job repository for testing."""
    return JobRepository()


@pytest.fixture(scope="session")
def sample_service(sample_repository):
    """Create a sample service for testing."""
    return SampleService(sample_repository)


@pytest.fixture(scope="session")
def genome_service(genome_repository, feature_repository, sample_service):
    """Create a genome service for testing."""
    return GenomeService(genome_repository, feature_repository, sample_service)


@pytest.fixture(scope="session")
def job_service(job_repository, sample_service):
    """Create a job service for testing."""
    return JobService(job_repository, sample_service)


@pytest.fixture
def clear_repositories(sample_repository, genome_repository, feature_repository, job_repository):
    """Clear all repositories before each test."""
    sample_repository.samples = {}
    sample_repository.sample_ids = {}
    genome_repository.genomes = {}
    feature_repository.features = {}
    job_repository.jobs = {}


@pytest.fixture
def test_sample(sample_service, clear_repositories):
    """Create a test sample."""
    sample = Sample(
        name="Test Sample",
        sample_type="blood",
        created_by="test_user"
    )
    return sample_service.create_sample(sample)


@pytest.fixture
def test_genome(genome_service, clear_repositories):
    """Create a test genome."""
    genome_data = {
        "name": "Human Genome",
        "species": "Homo sapiens",
        "assembly_version": "GRCh38",
        "created_by": "test_user",
        "fasta_path": "/path/to/genome.fa"
    }
    return genome_service.create_genome(genome_data)


@pytest.fixture
def test_feature(genome_service, test_genome):
    """Create a test feature."""
    feature_data = {
        "name": "BRCA1",
        "feature_type": "GENE",
        "chromosome": "chr17",
        "start": 43044295,
        "end": 43125483,
        "genome_id": str(test_genome.id),
        "created_by": "test_user",
        "strand": "+"
    }
    return genome_service.create_feature(feature_data)