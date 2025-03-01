"""Genome model for BLIMS."""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID, uuid4


class Genome:
    """A genome in the LIMS system.
    
    Genomes represent reference sequences against which samples can be aligned,
    annotated, or compared. They link to FASTA files and can have associated
    features.
    """
    
    def __init__(
        self,
        name: str,
        species: str,
        assembly_version: str,
        created_by: str,
        id: Optional[Union[UUID, str]] = None,
        description: Optional[str] = None,
        fasta_path: Optional[str] = None,
        index_paths: Optional[Dict[str, str]] = None,
        sample_id: Optional[Union[UUID, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a new Genome.
        
        Args:
            name: The name of the genome
            species: The species this genome represents
            assembly_version: Version of the genome assembly (e.g., GRCh38, hg19)
            created_by: The user who created this genome
            id: Unique identifier (generated if not provided)
            description: Optional description of the genome
            fasta_path: Path to the genome FASTA file
            index_paths: Dictionary of paths to genome indices (key=tool, value=path)
            sample_id: Optional ID of a sample this genome is derived from
            metadata: Additional metadata as key-value pairs
        """
        self.id = id or uuid4()
        self.name = name
        self.species = species
        self.assembly_version = assembly_version
        self.created_by = created_by
        self.created_at = datetime.now()
        self.description = description
        self.fasta_path = fasta_path
        self.index_paths = index_paths or {}
        self.sample_id = sample_id
        self.metadata = metadata or {}
        self.feature_ids: List[UUID] = []
        
    def add_feature(self, feature_id: Union[UUID, str]) -> None:
        """Add a feature to this genome.
        
        Args:
            feature_id: The ID of the feature to add
        """
        feature_id_uuid = feature_id if isinstance(feature_id, UUID) else UUID(str(feature_id))
        if feature_id_uuid not in self.feature_ids:
            self.feature_ids.append(feature_id_uuid)
    
    def add_index(self, tool: str, path: str) -> None:
        """Add or update an index path for this genome.
        
        Args:
            tool: The name of the tool this index is for (e.g., 'bwa', 'bowtie2')
            path: Path to the index
        """
        self.index_paths[tool] = path
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update metadata for this genome.
        
        Args:
            key: The metadata field name
            value: The metadata value
        """
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert this genome to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the genome
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "species": self.species,
            "assembly_version": self.assembly_version,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "fasta_path": self.fasta_path,
            "index_paths": self.index_paths,
            "sample_id": str(self.sample_id) if self.sample_id else None,
            "feature_ids": [str(fid) for fid in self.feature_ids],
            "metadata": self.metadata
        }