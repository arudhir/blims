"""Tests for the Sample model."""
import pytest
from uuid import UUID

from blims.models.sample import Sample


class TestSample:
    """Test cases for the Sample model."""
    
    def test_sample_init(self):
        """Test sample initialization with default values."""
        sample = Sample(name="Test Sample", sample_type="Blood", created_by="Test User")
        
        assert sample.name == "Test Sample"
        assert sample.sample_type == "Blood"
        assert sample.created_by == "Test User"
        assert isinstance(sample.id, UUID)
        assert sample.metadata == {}
        assert sample.parent_ids == []
        assert sample.file_paths == []
        assert sample.child_ids == []
    
    def test_sample_with_metadata(self):
        """Test sample with metadata."""
        metadata = {"concentration": "5ng/uL", "volume": "10uL", "quality": "high"}
        sample = Sample(
            name="Test Sample",
            sample_type="Blood",
            created_by="Test User",
            metadata=metadata,
        )
        
        assert sample.metadata == metadata
        
        # Test adding metadata
        sample.add_metadata("temperature", "4C")
        assert sample.metadata["temperature"] == "4C"
        
        # Test updating metadata
        sample.add_metadata("concentration", "10ng/uL")
        assert sample.metadata["concentration"] == "10ng/uL"
    
    def test_sample_with_files(self):
        """Test sample with file paths."""
        file_paths = ["/data/sample1.fastq", "/data/sample1.bam"]
        sample = Sample(
            name="Test Sample",
            sample_type="DNA",
            created_by="Test User",
            file_paths=file_paths,
        )
        
        assert sample.file_paths == file_paths
        
        # Test adding a file
        sample.add_file("/data/sample1_qc.txt")
        assert "/data/sample1_qc.txt" in sample.file_paths
        
        # Test adding a duplicate file (should not add)
        original_length = len(sample.file_paths)
        sample.add_file("/data/sample1.bam")
        assert len(sample.file_paths) == original_length
    
    def test_sample_lineage(self):
        """Test sample lineage (parents and children)."""
        parent_id1 = UUID("00000000-0000-0000-0000-000000000001")
        parent_id2 = UUID("00000000-0000-0000-0000-000000000002")
        
        sample = Sample(
            name="Derived Sample",
            sample_type="DNA Extract",
            created_by="Test User",
            parent_ids=[parent_id1, parent_id2],
        )
        
        assert len(sample.parent_ids) == 2
        assert parent_id1 in sample.parent_ids
        assert parent_id2 in sample.parent_ids
        
        # Test adding a parent
        parent_id3 = UUID("00000000-0000-0000-0000-000000000003")
        sample.add_parent(parent_id3)
        assert parent_id3 in sample.parent_ids
        
        # Test adding a child
        child_id = UUID("00000000-0000-0000-0000-000000000004")
        sample.add_child(child_id)
        assert child_id in sample.child_ids
        
        # Test adding a duplicate parent (should not add)
        original_length = len(sample.parent_ids)
        sample.add_parent(parent_id1)
        assert len(sample.parent_ids) == original_length
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        sample = Sample(
            name="Test Sample",
            sample_type="RNA",
            created_by="Test User",
            metadata={"quality": "high"},
        )
        
        # Add a child
        child_id = UUID("00000000-0000-0000-0000-000000000001")
        sample.add_child(child_id)
        
        # Convert to dict
        sample_dict = sample.to_dict()
        
        # Check properties
        assert sample_dict["name"] == "Test Sample"
        assert sample_dict["sample_type"] == "RNA"
        assert sample_dict["created_by"] == "Test User"
        assert sample_dict["metadata"] == {"quality": "high"}
        assert sample_dict["child_ids"] == [str(child_id)]
        

