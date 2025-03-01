"""Service for managing genomes and features in BLIMS."""

import os
from typing import Dict, List, Optional, Any, Union, Tuple
import uuid

from blims.models.genome import Genome
from blims.models.feature import Feature, FeatureType
from blims.repositories.genome_repository import GenomeRepository
from blims.repositories.feature_repository import FeatureRepository
from blims.services.sample_service import SampleService


class GenomeService:
    """Service for managing genomes and genomic features.
    
    This service provides business logic for creating, updating, and querying
    genomes and genomic features, as well as operations that span both.
    """
    
    def __init__(
        self, 
        genome_repository: GenomeRepository,
        feature_repository: FeatureRepository,
        sample_service: Optional[SampleService] = None
    ):
        """Initialize the genome service.
        
        Args:
            genome_repository: Repository for genome persistence
            feature_repository: Repository for feature persistence
            sample_service: Optional service for sample operations
        """
        self.genome_repository = genome_repository
        self.feature_repository = feature_repository
        self.sample_service = sample_service
    
    # Genome methods
    def create_genome(self, genome_data: Dict[str, Any]) -> Genome:
        """Create a new genome.
        
        Args:
            genome_data: Dictionary with genome information
            
        Returns:
            The created genome
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        required_fields = ['name', 'species', 'assembly_version', 'created_by']
        for field in required_fields:
            if field not in genome_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate sample_id if provided
        if 'sample_id' in genome_data and genome_data['sample_id'] and self.sample_service:
            sample_id = genome_data['sample_id']
            sample = self.sample_service.get_sample(sample_id)
            if not sample:
                raise ValueError(f"Sample with ID {sample_id} not found")
        
        # Create genome
        genome = Genome(
            name=genome_data['name'],
            species=genome_data['species'],
            assembly_version=genome_data['assembly_version'],
            created_by=genome_data['created_by'],
            description=genome_data.get('description'),
            fasta_path=genome_data.get('fasta_path'),
            index_paths=genome_data.get('index_paths'),
            sample_id=genome_data.get('sample_id'),
            metadata=genome_data.get('metadata', {})
        )
        
        # If sample_id is provided, add genome to sample
        if 'sample_id' in genome_data and genome_data['sample_id'] and self.sample_service:
            try:
                sample = self.sample_service.get_sample(genome_data['sample_id'])
                if sample:
                    sample.add_genome(genome.id)
                    self.sample_service.update_sample(sample)
            except Exception as e:
                # Log error but continue with genome creation
                print(f"Warning: Failed to update sample with genome: {str(e)}")
        
        return self.genome_repository.create_genome(genome)
    
    def get_genome(self, genome_id: Union[str, uuid.UUID]) -> Optional[Genome]:
        """Get a genome by ID.
        
        Args:
            genome_id: The ID of the genome to retrieve
            
        Returns:
            The genome if found, None otherwise
        """
        return self.genome_repository.get_genome(genome_id)
    
    def get_all_genomes(self) -> List[Genome]:
        """Get all genomes.
        
        Returns:
            List of all genomes
        """
        return self.genome_repository.get_all_genomes()
    
    def update_genome(self, genome_id: Union[str, uuid.UUID], update_data: Dict[str, Any]) -> Genome:
        """Update a genome with new data.
        
        Args:
            genome_id: The ID of the genome to update
            update_data: Dictionary with fields to update
            
        Returns:
            The updated genome
            
        Raises:
            ValueError: If the genome doesn't exist or data is invalid
        """
        genome = self.genome_repository.get_genome(genome_id)
        if not genome:
            raise ValueError(f"Genome with ID {genome_id} not found")
        
        # Update basic fields
        if 'name' in update_data:
            genome.name = update_data['name']
        if 'species' in update_data:
            genome.species = update_data['species']
        if 'assembly_version' in update_data:
            genome.assembly_version = update_data['assembly_version']
        if 'description' in update_data:
            genome.description = update_data['description']
        if 'fasta_path' in update_data:
            genome.fasta_path = update_data['fasta_path']
        
        # Update index paths
        if 'index_paths' in update_data:
            for tool, path in update_data['index_paths'].items():
                genome.add_index(tool, path)
        
        # Update metadata
        if 'metadata' in update_data:
            for key, value in update_data['metadata'].items():
                genome.update_metadata(key, value)
        
        return self.genome_repository.update_genome(genome)
    
    def delete_genome(self, genome_id: Union[str, uuid.UUID]) -> bool:
        """Delete a genome.
        
        Args:
            genome_id: The ID of the genome to delete
            
        Returns:
            True if the genome was deleted, False if it didn't exist
        """
        # Also delete all features associated with this genome
        features = self.feature_repository.get_features_by_genome(genome_id)
        for feature in features:
            self.feature_repository.delete_feature(feature.id)
            
        return self.genome_repository.delete_genome(genome_id)
    
    # Feature methods
    def create_feature(self, feature_data: Dict[str, Any]) -> Feature:
        """Create a new feature.
        
        Args:
            feature_data: Dictionary with feature information
            
        Returns:
            The created feature
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        required_fields = ['name', 'feature_type', 'chromosome', 'start', 'end', 'genome_id', 'created_by']
        for field in required_fields:
            if field not in feature_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Validate genome_id
        genome_id = feature_data['genome_id']
        genome = self.genome_repository.get_genome(genome_id)
        if not genome:
            raise ValueError(f"Genome with ID {genome_id} not found")
        
        # Validate parent_id if provided
        if 'parent_id' in feature_data and feature_data['parent_id']:
            parent_id = feature_data['parent_id']
            parent = self.feature_repository.get_feature(parent_id)
            if not parent:
                raise ValueError(f"Parent feature with ID {parent_id} not found")
            
            # Validate parent and feature are in the same genome
            if str(parent.genome_id) != str(genome_id):
                raise ValueError("Parent feature must be in the same genome as the feature")
        
        # Create feature
        feature = Feature(
            name=feature_data['name'],
            feature_type=feature_data['feature_type'],
            chromosome=feature_data['chromosome'],
            start=int(feature_data['start']),
            end=int(feature_data['end']),
            genome_id=genome_id,
            created_by=feature_data['created_by'],
            strand=feature_data.get('strand'),
            description=feature_data.get('description'),
            sequence=feature_data.get('sequence'),
            parent_id=feature_data.get('parent_id'),
            metadata=feature_data.get('metadata', {})
        )
        
        # Add feature to genome
        genome.add_feature(feature.id)
        self.genome_repository.update_genome(genome)
        
        # Add feature to parent if applicable
        if 'parent_id' in feature_data and feature_data['parent_id']:
            parent = self.feature_repository.get_feature(feature_data['parent_id'])
            if parent:
                parent.add_child(feature.id)
                self.feature_repository.update_feature(parent)
        
        return self.feature_repository.create_feature(feature)
    
    def get_feature(self, feature_id: Union[str, uuid.UUID]) -> Optional[Feature]:
        """Get a feature by ID.
        
        Args:
            feature_id: The ID of the feature to retrieve
            
        Returns:
            The feature if found, None otherwise
        """
        return self.feature_repository.get_feature(feature_id)
    
    def get_genome_features(self, genome_id: Union[str, uuid.UUID]) -> List[Feature]:
        """Get all features for a specific genome.
        
        Args:
            genome_id: The ID of the genome
            
        Returns:
            List of features for the genome
        """
        return self.feature_repository.get_features_by_genome(genome_id)
    
    def get_features_in_region(self, genome_id: Union[str, uuid.UUID], chromosome: str, start: int, end: int) -> List[Feature]:
        """Get all features in a specific genomic region.
        
        Args:
            genome_id: The ID of the genome
            chromosome: The chromosome name
            start: Start position
            end: End position
            
        Returns:
            List of features in the region
        """
        return self.feature_repository.get_features_in_region(chromosome, start, end, genome_id)
    
    def import_features_from_gff(self, genome_id: Union[str, uuid.UUID], gff_path: str, created_by: str) -> int:
        """Import features from a GFF file.
        
        Args:
            genome_id: The ID of the genome to associate features with
            gff_path: Path to the GFF file
            created_by: The user importing the features
            
        Returns:
            Number of features imported
            
        Raises:
            ValueError: If the genome doesn't exist or file is invalid
            FileNotFoundError: If the GFF file doesn't exist
        """
        # Validate genome
        genome = self.genome_repository.get_genome(genome_id)
        if not genome:
            raise ValueError(f"Genome with ID {genome_id} not found")
            
        # Check file exists
        if not os.path.exists(gff_path):
            raise FileNotFoundError(f"GFF file not found: {gff_path}")
        
        # Import features
        count = 0
        # For future implementation: actual GFF parsing and feature creation
        # This would create Feature objects from GFF records and add them to the repository
        
        return count
    
    def get_feature_hierarchy(self, feature_id: Union[str, uuid.UUID]) -> Dict[str, Any]:
        """Get a feature and all its child features in a hierarchical structure.
        
        Args:
            feature_id: The ID of the parent feature
            
        Returns:
            Dictionary with the feature hierarchy
            
        Raises:
            ValueError: If the feature doesn't exist
        """
        feature = self.feature_repository.get_feature(feature_id)
        if not feature:
            raise ValueError(f"Feature with ID {feature_id} not found")
            
        return self._build_feature_hierarchy(feature)
    
    def _build_feature_hierarchy(self, feature: Feature) -> Dict[str, Any]:
        """Recursively build a feature hierarchy.
        
        Args:
            feature: The feature to build the hierarchy for
            
        Returns:
            Dictionary with the feature hierarchy
        """
        result = feature.to_dict()
        result['children'] = []
        
        # Get child features
        for child_id in feature.child_ids:
            child = self.feature_repository.get_feature(child_id)
            if child:
                result['children'].append(self._build_feature_hierarchy(child))
                
        return result