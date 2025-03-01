"""Tests for the SampleRepository."""
import pytest
from uuid import UUID

from blims.models.sample import Sample
from blims.core.repository import SampleRepository


class TestSampleRepository:
    """Test cases for the SampleRepository."""
    
    @pytest.fixture(autouse=True)
    def setup(self, sample_repository, clear_repository):
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
        self.repo.add(self.sample1)
        self.repo.add(self.sample2)
    
    def test_add_and_get(self):
        """Test adding and retrieving samples."""
        # Get existing sample
        retrieved = self.repo.get(UUID("00000000-0000-0000-0000-000000000001"))
        assert retrieved == self.sample1
        
        # Get non-existent sample
        non_existent = self.repo.get(UUID("00000000-0000-0000-0000-000000000999"))
        assert non_existent is None
        
        # Test duplicate add raises error
        with pytest.raises(ValueError):
            self.repo.add(self.sample1)
    
    def test_get_all(self):
        """Test retrieving all samples."""
        all_samples = self.repo.get_all()
        assert len(all_samples) == 2
        assert self.sample1 in all_samples
        assert self.sample2 in all_samples
    
    def test_get_by_metadata(self):
        """Test getting samples by metadata."""
        # Get samples by existing metadata
        samples1 = self.repo.get_by_metadata("property", "value1")
        assert len(samples1) == 1
        assert samples1[0] == self.sample1
        
        # Get samples by non-existent metadata
        samples_none = self.repo.get_by_metadata("nonexistent", "value")
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
        
        # Add child sample
        self.repo.add(child)
        
        # Check that parent has child
        assert UUID("00000000-0000-0000-0000-000000000003") in self.sample1.child_ids
        
        # Check ancestry
        ancestors = self.repo.get_ancestry(UUID("00000000-0000-0000-0000-000000000003"))
        assert len(ancestors) == 1
        assert ancestors[0] == self.sample1
        
        # Check descendants
        descendants = self.repo.get_descendants(UUID("00000000-0000-0000-0000-000000000001"))
        assert len(descendants) == 1
        assert descendants[0] == child
        
        # Test ancestry with non-existent sample
        with pytest.raises(ValueError):
            self.repo.get_ancestry(UUID("00000000-0000-0000-0000-000000000999"))
        
        # Test descendants with non-existent sample
        with pytest.raises(ValueError):
            self.repo.get_descendants(UUID("00000000-0000-0000-0000-000000000999"))


