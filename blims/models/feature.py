"""Feature model for BLIMS."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple
from uuid import UUID, uuid4


class FeatureType(str, Enum):
    """Types of genomic features."""
    
    GENE = "GENE"
    EXON = "EXON"
    CDS = "CDS"
    PROMOTER = "PROMOTER"
    ENHANCER = "ENHANCER"
    SNP = "SNP"
    INDEL = "INDEL"
    CNV = "CNV"
    SV = "SV"  # Structural Variant
    REPEAT = "REPEAT"
    REGULATORY = "REGULATORY"
    CUSTOM = "CUSTOM"


class Feature:
    """A genomic feature in the LIMS system.
    
    Features represent annotated regions in a genome, such as genes,
    exons, variants, or regulatory elements.
    """
    
    def __init__(
        self,
        name: str,
        feature_type: Union[FeatureType, str],
        chromosome: str,
        start: int,
        end: int,
        genome_id: Union[UUID, str],
        created_by: str,
        id: Optional[Union[UUID, str]] = None,
        strand: Optional[str] = None,
        description: Optional[str] = None,
        sequence: Optional[str] = None,
        parent_id: Optional[Union[UUID, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a new Feature.
        
        Args:
            name: The name of the feature (e.g., gene name, variant ID)
            feature_type: The type of feature
            chromosome: Chromosome or contig name
            start: Start position (1-based)
            end: End position (inclusive)
            genome_id: ID of the genome this feature belongs to
            created_by: The user who created this feature
            id: Unique identifier (generated if not provided)
            strand: Strand ('+', '-', or None for unstranded)
            description: Optional description of the feature
            sequence: Optional nucleotide sequence of the feature
            parent_id: Optional ID of a parent feature (e.g., gene for an exon)
            metadata: Additional metadata as key-value pairs
        """
        self.id = id or uuid4()
        self.name = name
        self.feature_type = feature_type if isinstance(feature_type, FeatureType) else FeatureType(feature_type)
        self.chromosome = chromosome
        self.start = start
        self.end = end
        self.genome_id = genome_id
        self.created_by = created_by
        self.created_at = datetime.now()
        self.strand = strand
        self.description = description
        self.sequence = sequence
        self.parent_id = parent_id
        self.metadata = metadata or {}
        self.child_ids: List[UUID] = []
    
    def get_position(self) -> Tuple[str, int, int, Optional[str]]:
        """Get the genomic position of this feature.
        
        Returns:
            Tuple of (chromosome, start, end, strand)
        """
        return (self.chromosome, self.start, self.end, self.strand)
    
    def get_length(self) -> int:
        """Get the length of this feature in base pairs.
        
        Returns:
            Length of the feature
        """
        return self.end - self.start + 1
    
    def add_child(self, feature_id: Union[UUID, str]) -> None:
        """Add a child feature to this feature.
        
        Args:
            feature_id: The ID of the child feature
        """
        feature_id_uuid = feature_id if isinstance(feature_id, UUID) else UUID(str(feature_id))
        if feature_id_uuid not in self.child_ids:
            self.child_ids.append(feature_id_uuid)
    
    def update_metadata(self, key: str, value: Any) -> None:
        """Update metadata for this feature.
        
        Args:
            key: The metadata field name
            value: The metadata value
        """
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert this feature to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the feature
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "feature_type": self.feature_type.value,
            "chromosome": self.chromosome,
            "start": self.start,
            "end": self.end,
            "strand": self.strand,
            "genome_id": str(self.genome_id),
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "sequence": self.sequence,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "child_ids": [str(cid) for cid in self.child_ids],
            "metadata": self.metadata
        }