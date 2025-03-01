"""Tests for the SampleService."""
import unittest
from unittest.mock import Mock, patch
from uuid import UUID

from blims.models.sample import Sample
from blims.core.repository import SampleRepository
from blims.core.service import SampleService


class TestSampleService(unittest.TestCase):
    """Test cases for the SampleService."""
    
    def setUp(self):
        """Set up test cases."""
        self.repo = SampleRepository()
        self.service = SampleService(repository=self.repo)
        
        # Create a sample to be used as a parent
        self.parent_sample = Sample(
            name="Parent Sample",
            sample_type="Blood",
            created_by="Test User",
            id=UUID("00000000-0000-0000-0000-000000000001"),
        )
        
        # Add to repository
        self.repo.add(self.parent_sample)
    
    def test_create_sample(self):
        """Test creating a sample."""
        # Create a new sample
        sample = self.service.create_sample(
            name="New Sample",
            sample_type="DNA",
            created_by="Test User",
            metadata={"property": "value"}
        )
        
        # Verify sample was created correctly
        self.assertEqual(sample.name, "New Sample")
        self.assertEqual(sample.sample_type, "DNA")
        self.assertEqual(sample.created_by, "Test User")
        self.assertEqual(sample.metadata, {"property": "value"})
        
        # Verify sample was added to repository
        retrieved = self.repo.get(sample.id)
        self.assertEqual(retrieved, sample)
    
    def test_create_sample_with_invalid_parent(self):
        """Test creating a sample with an invalid parent ID."""
        # Try to create a sample with non-existent parent
        with self.assertRaises(ValueError):
            self.service.create_sample(
                name="New Sample",
                sample_type="DNA",
                created_by="Test User",
                parent_ids=[UUID("00000000-0000-0000-0000-000000000999")]
            )
    
    def test_derive_sample(self):
        """Test deriving a sample from a parent."""
        # Derive a new sample
        derived = self.service.derive_sample(
            parent_id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Derived Sample",
            sample_type="DNA Extract",
            created_by="Test User",
            metadata={"extraction_method": "column"}
        )
        
        # Verify derived sample properties
        self.assertEqual(derived.name, "Derived Sample")
        self.assertEqual(derived.parent_ids, [UUID("00000000-0000-0000-0000-000000000001")])
        self.assertEqual(derived.metadata, {"extraction_method": "column"})
        
        # Verify parent-child relationship
        self.assertIn(derived.id, self.parent_sample.child_ids)
    
    def test_derive_sample_invalid_parent(self):
        """Test deriving from a non-existent parent."""
        with self.assertRaises(ValueError):
            self.service.derive_sample(
                parent_id=UUID("00000000-0000-0000-0000-000000000999"),
                name="Derived Sample",
                sample_type="DNA Extract",
                created_by="Test User"
            )
    
    def test_add_metadata_to_sample(self):
        """Test adding metadata to a sample."""
        # Add metadata
        sample = self.service.add_metadata_to_sample(
            UUID("00000000-0000-0000-0000-000000000001"),
            "new_key",
            "new_value"
        )
        
        # Verify metadata was added
        self.assertEqual(sample.metadata["new_key"], "new_value")
    
    def test_add_metadata_to_nonexistent_sample(self):
        """Test adding metadata to a non-existent sample."""
        with self.assertRaises(ValueError):
            self.service.add_metadata_to_sample(
                UUID("00000000-0000-0000-0000-000000000999"),
                "key",
                "value"
            )
    
    def test_add_file_to_sample(self):
        """Test adding a file to a sample."""
        # Add file
        sample = self.service.add_file_to_sample(
            UUID("00000000-0000-0000-0000-000000000001"),
            "/path/to/file.txt"
        )
        
        # Verify file was added
        self.assertIn("/path/to/file.txt", sample.file_paths)
    
    def test_add_file_to_nonexistent_sample(self):
        """Test adding a file to a non-existent sample."""
        with self.assertRaises(ValueError):
            self.service.add_file_to_sample(
                UUID("00000000-0000-0000-0000-000000000999"),
                "/path/to/file.txt"
            )
    
    def test_get_sample_lineage(self):
        """Test getting a sample's lineage."""
        # Create a derived sample
        derived = self.service.derive_sample(
            parent_id=UUID("00000000-0000-0000-0000-000000000001"),
            name="Derived Sample",
            sample_type="DNA Extract",
            created_by="Test User"
        )
        
        # Get lineage for derived sample
        lineage = self.service.get_sample_lineage(derived.id)
        
        # Verify ancestors and descendants
        self.assertEqual(len(lineage["ancestors"]), 1)
        self.assertEqual(lineage["ancestors"][0], self.parent_sample)
        self.assertEqual(len(lineage["descendants"]), 0)
        
        # Get lineage for parent sample
        lineage = self.service.get_sample_lineage(self.parent_sample.id)
        
        # Verify ancestors and descendants
        self.assertEqual(len(lineage["ancestors"]), 0)
        self.assertEqual(len(lineage["descendants"]), 1)
        self.assertEqual(lineage["descendants"][0], derived)
    
    def test_get_lineage_nonexistent_sample(self):
        """Test getting lineage for a non-existent sample."""
        with self.assertRaises(ValueError):
            self.service.get_sample_lineage(UUID("00000000-0000-0000-0000-000000000999"))
    
    def test_search_samples(self):
        """Test searching for samples by metadata."""
        # Create samples with searchable metadata
        self.service.create_sample(
            name="Sample A",
            sample_type="DNA",
            created_by="Test User",
            metadata={"category": "routine", "priority": "high"}
        )
        
        self.service.create_sample(
            name="Sample B",
            sample_type="RNA",
            created_by="Test User",
            metadata={"category": "research", "priority": "high"}
        )
        
        self.service.create_sample(
            name="Sample C",
            sample_type="DNA",
            created_by="Test User",
            metadata={"category": "routine", "priority": "low"}
        )
        
        # Search by single filter
        results = self.service.search_samples({"category": "routine"})
        self.assertEqual(len(results), 2)
        
        # Search by multiple filters
        results = self.service.search_samples({"category": "routine", "priority": "high"})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Sample A")
        
        # Search with no matching results
        results = self.service.search_samples({"category": "nonexistent"})
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()