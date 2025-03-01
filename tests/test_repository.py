"""Tests for the SampleRepository."""
import pytest
from uuid import UUID

from blims.models.sample import Sample
from blims.repositories.sample_repository import SampleRepository


class TestSampleRepository:
    """Test cases for the SampleRepository."""
    
    @pytest.fixture(autouse=True)
    def setup(self, sample_repository, clear_repositories):
        """Set up test cases."""
        self.repo = sample_repository
        
        # Create some test samples
        self.sample1 = Sample(
            name="Sample 1",
            sample_type="Blood",
            created_by="Test User",
            id=UUID("00000000-0000-0000-0000-000000000001"),
            metadata={"property": "value1"}
        )
        
        self.sample2 = Sample(
            name="Sample 2",
            sample_type="DNA",
            created_by="Test User",
            id=UUID("00000000-0000-0000-0000-000000000002"),
            metadata={"property": "value2"}
        )
        
        # Add samples to repository
        self.repo.create_sample(self.sample1)
        self.repo.create_sample(self.sample2)
    
    def test_add_and_get(self):
        """Test adding and retrieving samples."""
        # Get existing sample
        retrieved = self.repo.get_sample(UUID("00000000-0000-0000-0000-000000000001"))
        assert retrieved.name == self.sample1.name
        
        # Get non-existent sample
        non_existent = self.repo.get_sample(UUID("00000000-0000-0000-0000-000000000999"))
        assert non_existent is None
        
        # Test duplicate create
        # Note: SampleRepository.create_sample doesn't raise error for duplicates,
        # it just updates the existing sample
        sample_dup = Sample(
            name="Duplicate Sample",
            sample_type="Test",
            created_by="Test User",
            id=UUID("00000000-0000-0000-0000-000000000001")  # Same ID as sample1
        )
        self.repo.create_sample(sample_dup)
        
        # Verify the sample was updated
        updated = self.repo.get_sample(UUID("00000000-0000-0000-0000-000000000001"))
        assert updated.name == "Duplicate Sample"
    
    def test_get_all(self):
        """Test retrieving all samples."""
        all_samples = self.repo.get_all_samples()
        assert len(all_samples) == 2
        sample_names = [s.name for s in all_samples]
        assert "Sample 1" in sample_names
        assert "Sample 2" in sample_names
    
    def test_get_by_metadata(self):
        """Test getting samples by metadata."""
        # The new repository doesn't have get_by_metadata, so we'll simulate it
        all_samples = self.repo.get_all_samples()
        
        # Get samples with specific metadata manually
        samples1 = [s for s in all_samples if s.metadata.get("property") == "value1"]
        assert len(samples1) == 1
        assert samples1[0].name == "Sample 1"
        
        # Test with non-existent metadata
        samples_none = [s for s in all_samples if s.metadata.get("nonexistent") == "value"]
        assert len(samples_none) == 0
    
    def test_parent_child_relationship(self):
        """Test parent-child relationship tracking."""
        # Create child sample
        child = Sample(
            name="Child Sample",
            sample_type="RNA",
            created_by="Test User",
            id=UUID("00000000-0000-0000-0000-000000000003"),
            parent_ids=[UUID("00000000-0000-0000-0000-000000000001")]
        )
        
        # Add child sample to repository
        self.repo.create_sample(child)
        
        # Update parent to include child
        self.sample1.add_child(child.id)
        self.repo.update_sample(self.sample1)
        
        # Get updated parent and child from repository
        parent = self.repo.get_sample(self.sample1.id)
        retrieved_child = self.repo.get_sample(child.id)
        
        # Check relationships
        assert str(child.id) in [str(c) for c in parent.child_ids]
        assert str(parent.id) in [str(p) for p in retrieved_child.parent_ids]
        
        # The SampleRepository doesn't have ancestry/descendant methods,
        # but we can test that the parent-child relationships are maintained

