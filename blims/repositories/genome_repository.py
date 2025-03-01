"""Repository for managing genomes."""

from typing import Dict, List, Optional, Union
import uuid

from blims.models.genome import Genome


class GenomeRepository:
    """Repository for managing genomes.
    
    This repository handles the storage and retrieval of Genome objects, with
    methods for creating, updating, and querying genomes.
    """
    
    def __init__(self):
        """Initialize the genome repository."""
        self.genomes: Dict[str, Genome] = {}
    
    def create_genome(self, genome: Genome) -> Genome:
        """Store a new genome in the repository.
        
        Args:
            genome: The genome to store
            
        Returns:
            The stored genome with any repository-assigned fields
        """
        genome_id = str(genome.id)
        self.genomes[genome_id] = genome
        return genome
    
    def get_genome(self, genome_id: Union[str, uuid.UUID]) -> Optional[Genome]:
        """Retrieve a genome by its ID.
        
        Args:
            genome_id: The ID of the genome to retrieve
            
        Returns:
            The genome if found, None otherwise
        """
        genome_id_str = str(genome_id)
        return self.genomes.get(genome_id_str)
    
    def update_genome(self, genome: Genome) -> Genome:
        """Update an existing genome.
        
        Args:
            genome: The genome with updated fields
            
        Returns:
            The updated genome
            
        Raises:
            ValueError: If the genome doesn't exist
        """
        genome_id = str(genome.id)
        if genome_id not in self.genomes:
            raise ValueError(f"Genome with ID {genome_id} not found")
        
        self.genomes[genome_id] = genome
        return genome
    
    def delete_genome(self, genome_id: Union[str, uuid.UUID]) -> bool:
        """Delete a genome from the repository.
        
        Args:
            genome_id: The ID of the genome to delete
            
        Returns:
            True if the genome was deleted, False if it didn't exist
        """
        genome_id_str = str(genome_id)
        if genome_id_str in self.genomes:
            del self.genomes[genome_id_str]
            return True
        return False
    
    def get_all_genomes(self) -> List[Genome]:
        """Get all genomes in the repository.
        
        Returns:
            List of all genomes
        """
        return list(self.genomes.values())
    
    def get_genomes_by_species(self, species: str) -> List[Genome]:
        """Get all genomes for a specific species.
        
        Args:
            species: The species to filter by
            
        Returns:
            List of genomes for the specified species
        """
        return [g for g in self.genomes.values() if g.species == species]
    
    def get_genomes_by_assembly(self, assembly_version: str) -> List[Genome]:
        """Get all genomes with a specific assembly version.
        
        Args:
            assembly_version: The assembly version to filter by
            
        Returns:
            List of genomes with the specified assembly version
        """
        return [g for g in self.genomes.values() if g.assembly_version == assembly_version]
    
    def get_genomes_by_sample(self, sample_id: Union[str, uuid.UUID]) -> List[Genome]:
        """Get all genomes associated with a specific sample.
        
        Args:
            sample_id: The ID of the sample
            
        Returns:
            List of genomes associated with the sample
        """
        sample_id_str = str(sample_id)
        return [g for g in self.genomes.values() if g.sample_id and str(g.sample_id) == sample_id_str]