"""Repository for managing genomic features."""

from typing import Dict, List, Optional, Union
import uuid

from blims.models.feature import Feature, FeatureType


class FeatureRepository:
    """Repository for managing genomic features.
    
    This repository handles the storage and retrieval of Feature objects, with
    methods for creating, updating, and querying features.
    """
    
    def __init__(self):
        """Initialize the feature repository."""
        self.features: Dict[str, Feature] = {}
    
    def create_feature(self, feature: Feature) -> Feature:
        """Store a new feature in the repository.
        
        Args:
            feature: The feature to store
            
        Returns:
            The stored feature with any repository-assigned fields
        """
        feature_id = str(feature.id)
        self.features[feature_id] = feature
        return feature
    
    def get_feature(self, feature_id: Union[str, uuid.UUID]) -> Optional[Feature]:
        """Retrieve a feature by its ID.
        
        Args:
            feature_id: The ID of the feature to retrieve
            
        Returns:
            The feature if found, None otherwise
        """
        feature_id_str = str(feature_id)
        return self.features.get(feature_id_str)
    
    def update_feature(self, feature: Feature) -> Feature:
        """Update an existing feature.
        
        Args:
            feature: The feature with updated fields
            
        Returns:
            The updated feature
            
        Raises:
            ValueError: If the feature doesn't exist
        """
        feature_id = str(feature.id)
        if feature_id not in self.features:
            raise ValueError(f"Feature with ID {feature_id} not found")
        
        self.features[feature_id] = feature
        return feature
    
    def delete_feature(self, feature_id: Union[str, uuid.UUID]) -> bool:
        """Delete a feature from the repository.
        
        Args:
            feature_id: The ID of the feature to delete
            
        Returns:
            True if the feature was deleted, False if it didn't exist
        """
        feature_id_str = str(feature_id)
        if feature_id_str in self.features:
            del self.features[feature_id_str]
            return True
        return False
    
    def get_all_features(self) -> List[Feature]:
        """Get all features in the repository.
        
        Returns:
            List of all features
        """
        return list(self.features.values())
    
    def get_features_by_genome(self, genome_id: Union[str, uuid.UUID]) -> List[Feature]:
        """Get all features for a specific genome.
        
        Args:
            genome_id: The ID of the genome
            
        Returns:
            List of features for the specified genome
        """
        genome_id_str = str(genome_id)
        return [f for f in self.features.values() if str(f.genome_id) == genome_id_str]
    
    def get_features_by_type(self, feature_type: Union[str, FeatureType], genome_id: Optional[Union[str, uuid.UUID]] = None) -> List[Feature]:
        """Get all features of a specific type.
        
        Args:
            feature_type: The feature type to filter by
            genome_id: Optional genome ID to further filter results
            
        Returns:
            List of features with the specified type
        """
        type_str = feature_type.value if isinstance(feature_type, FeatureType) else feature_type
        
        if genome_id:
            genome_id_str = str(genome_id)
            return [f for f in self.features.values() 
                    if f.feature_type.value == type_str and str(f.genome_id) == genome_id_str]
        
        return [f for f in self.features.values() if f.feature_type.value == type_str]
    
    def get_features_by_chromosome(self, chromosome: str, genome_id: Union[str, uuid.UUID]) -> List[Feature]:
        """Get all features on a specific chromosome of a genome.
        
        Args:
            chromosome: The chromosome name
            genome_id: The ID of the genome
            
        Returns:
            List of features on the specified chromosome
        """
        genome_id_str = str(genome_id)
        return [f for f in self.features.values() 
                if f.chromosome == chromosome and str(f.genome_id) == genome_id_str]
    
    def get_features_in_region(self, chromosome: str, start: int, end: int, genome_id: Union[str, uuid.UUID]) -> List[Feature]:
        """Get all features within a genomic region.
        
        Args:
            chromosome: The chromosome name
            start: Start position
            end: End position
            genome_id: The ID of the genome
            
        Returns:
            List of features overlapping the specified region
        """
        genome_id_str = str(genome_id)
        return [f for f in self.features.values() 
                if f.chromosome == chromosome 
                and str(f.genome_id) == genome_id_str
                and f.start <= end and f.end >= start]
    
    def get_features_by_parent(self, parent_id: Union[str, uuid.UUID]) -> List[Feature]:
        """Get all child features of a parent feature.
        
        Args:
            parent_id: The ID of the parent feature
            
        Returns:
            List of child features
        """
        parent_id_str = str(parent_id)
        return [f for f in self.features.values() 
                if f.parent_id and str(f.parent_id) == parent_id_str]