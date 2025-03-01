"""Sample repository for storing and retrieving samples."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from blims.models.sample import Sample


class SampleRepository:
    """Repository for managing sample records.

    This class provides an interface for storing, retrieving, and
    querying samples in the LIMS system.
    """

    def __init__(self):
        """Initialize a new sample repository."""
        self._samples: Dict[UUID, Sample] = {}

    def add(self, sample: Sample) -> None:
        """Add a sample to the repository.

        Args:
            sample: The sample to add

        Raises:
            ValueError: If a sample with the same ID already exists
        """
        if sample.id in self._samples:
            raise ValueError(f"Sample with ID {sample.id} already exists")

        # Update parent-child relationships
        for parent_id in sample.parent_ids:
            if parent_id in self._samples:
                self._samples[parent_id].add_child(sample.id)

        self._samples[sample.id] = sample

    def get(self, sample_id: UUID) -> Optional[Sample]:
        """Get a sample by ID.

        Args:
            sample_id: The ID of the sample to retrieve

        Returns:
            The sample if found, None otherwise
        """
        return self._samples.get(sample_id)

    def get_all(self) -> List[Sample]:
        """Get all samples in the repository.

        Returns:
            List of all samples
        """
        return list(self._samples.values())

    def get_by_metadata(self, key: str, value: Any) -> List[Sample]:
        """Get samples that have the specified metadata.

        Args:
            key: The metadata key to search for
            value: The metadata value to match

        Returns:
            List of samples with matching metadata
        """
        return [
            sample
            for sample in self._samples.values()
            if key in sample.metadata and sample.metadata[key] == value
        ]

    def get_ancestry(self, sample_id: UUID) -> List[Sample]:
        """Get the complete lineage tree of a sample's ancestors.

        Args:
            sample_id: The ID of the sample to get ancestry for

        Returns:
            List of all parent samples in the lineage tree

        Raises:
            ValueError: If the sample does not exist
        """
        if sample_id not in self._samples:
            raise ValueError(f"Sample with ID {sample_id} does not exist")

        sample = self._samples[sample_id]
        ancestors = []

        # Recursively collect all ancestors
        for parent_id in sample.parent_ids:
            parent = self.get(parent_id)
            if parent:
                ancestors.append(parent)
                ancestors.extend(self.get_ancestry(parent_id))

        return ancestors

    def get_descendants(self, sample_id: UUID) -> List[Sample]:
        """Get all descendants of a sample.

        Args:
            sample_id: The ID of the sample to get descendants for

        Returns:
            List of all child samples in the lineage tree

        Raises:
            ValueError: If the sample does not exist
        """
        if sample_id not in self._samples:
            raise ValueError(f"Sample with ID {sample_id} does not exist")

        sample = self._samples[sample_id]
        descendants = []

        # Recursively collect all descendants
        for child_id in sample.child_ids:
            child = self.get(child_id)
            if child:
                descendants.append(child)
                descendants.extend(self.get_descendants(child_id))

        return descendants
