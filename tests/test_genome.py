"""Test cases for genome models, repositories, and services."""

import unittest
import uuid
from datetime import datetime

from blims.models.genome import Genome
from blims.models.feature import Feature, FeatureType
from blims.repositories.genome_repository import GenomeRepository
from blims.repositories.feature_repository import FeatureRepository
from blims.services.genome_service import GenomeService
from blims.services.sample_service import SampleService
from blims.repositories.sample_repository import SampleRepository
from blims.models.sample import Sample


class TestGenomeModel(unittest.TestCase):
    """Test cases for the Genome model."""
    
    def test_genome_initialization(self):
        """Test the initialization of a Genome object."""
        # Create a genome
        genome = Genome(
            name="Human Genome",
            species="Homo sapiens",
            assembly_version="GRCh38",
            created_by="test_user",
            description="Human reference genome",
            fasta_path="/path/to/genome.fa"
        )
        
        # Check attributes
        self.assertEqual(genome.name, "Human Genome")
        self.assertEqual(genome.species, "Homo sapiens")
        self.assertEqual(genome.assembly_version, "GRCh38")
        self.assertEqual(genome.created_by, "test_user")
        self.assertEqual(genome.description, "Human reference genome")
        self.assertEqual(genome.fasta_path, "/path/to/genome.fa")
        self.assertIsInstance(genome.id, uuid.UUID)
        self.assertIsInstance(genome.created_at, datetime)
        self.assertEqual(genome.index_paths, {})
        self.assertEqual(genome.feature_ids, [])
        
    def test_add_feature(self):
        """Test adding a feature to a genome."""
        genome = Genome(
            name="Human Genome",
            species="Homo sapiens",
            assembly_version="GRCh38",
            created_by="test_user"
        )
        
        # Add a feature
        feature_id = uuid.uuid4()
        genome.add_feature(feature_id)
        
        # Check that the feature was added
        self.assertIn(feature_id, genome.feature_ids)
        self.assertEqual(len(genome.feature_ids), 1)
        
        # Add the same feature again (should not duplicate)
        genome.add_feature(feature_id)
        self.assertEqual(len(genome.feature_ids), 1)
        
        # Add another feature
        another_feature_id = uuid.uuid4()
        genome.add_feature(another_feature_id)
        self.assertEqual(len(genome.feature_ids), 2)
        
    def test_add_index(self):
        """Test adding an index to a genome."""
        genome = Genome(
            name="Human Genome",
            species="Homo sapiens",
            assembly_version="GRCh38",
            created_by="test_user"
        )
        
        # Add indices
        genome.add_index("bwa", "/path/to/bwa/index")
        genome.add_index("bowtie2", "/path/to/bowtie2/index")
        
        # Check indices
        self.assertEqual(len(genome.index_paths), 2)
        self.assertEqual(genome.index_paths["bwa"], "/path/to/bwa/index")
        self.assertEqual(genome.index_paths["bowtie2"], "/path/to/bowtie2/index")
        
        # Update an existing index
        genome.add_index("bwa", "/path/to/new/bwa/index")
        self.assertEqual(genome.index_paths["bwa"], "/path/to/new/bwa/index")
        
    def test_to_dict(self):
        """Test converting a genome to a dictionary."""
        genome = Genome(
            name="Human Genome",
            species="Homo sapiens",
            assembly_version="GRCh38",
            created_by="test_user",
            fasta_path="/path/to/genome.fa"
        )
        
        # Add an index and a feature
        genome.add_index("bwa", "/path/to/index")
        feature_id = uuid.uuid4()
        genome.add_feature(feature_id)
        
        # Convert to dictionary
        genome_dict = genome.to_dict()
        
        # Check dictionary values
        self.assertEqual(genome_dict["name"], "Human Genome")
        self.assertEqual(genome_dict["species"], "Homo sapiens")
        self.assertEqual(genome_dict["assembly_version"], "GRCh38")
        self.assertEqual(genome_dict["created_by"], "test_user")
        self.assertEqual(genome_dict["fasta_path"], "/path/to/genome.fa")
        self.assertIn("id", genome_dict)
        self.assertIn("created_at", genome_dict)
        self.assertEqual(genome_dict["index_paths"], {"bwa": "/path/to/index"})
        self.assertEqual(genome_dict["feature_ids"], [str(feature_id)])


class TestFeatureModel(unittest.TestCase):
    """Test cases for the Feature model."""
    
    def test_feature_initialization(self):
        """Test the initialization of a Feature object."""
        # Create a feature
        genome_id = uuid.uuid4()
        feature = Feature(
            name="BRCA1",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=43044295,
            end=43125483,
            genome_id=genome_id,
            created_by="test_user",
            strand="+",
            description="Breast cancer type 1 susceptibility protein"
        )
        
        # Check attributes
        self.assertEqual(feature.name, "BRCA1")
        self.assertEqual(feature.feature_type, FeatureType.GENE)
        self.assertEqual(feature.chromosome, "chr17")
        self.assertEqual(feature.start, 43044295)
        self.assertEqual(feature.end, 43125483)
        self.assertEqual(feature.genome_id, genome_id)
        self.assertEqual(feature.created_by, "test_user")
        self.assertEqual(feature.strand, "+")
        self.assertEqual(feature.description, "Breast cancer type 1 susceptibility protein")
        self.assertIsInstance(feature.id, uuid.UUID)
        self.assertIsInstance(feature.created_at, datetime)
        self.assertEqual(feature.child_ids, [])
        
    def test_get_position(self):
        """Test getting a feature's position."""
        feature = Feature(
            name="BRCA1",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=43044295,
            end=43125483,
            genome_id=uuid.uuid4(),
            created_by="test_user",
            strand="+"
        )
        
        # Get position
        position = feature.get_position()
        
        # Check position
        self.assertEqual(position, ("chr17", 43044295, 43125483, "+"))
        
    def test_get_length(self):
        """Test getting a feature's length."""
        feature = Feature(
            name="BRCA1",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=43044295,
            end=43125483,
            genome_id=uuid.uuid4(),
            created_by="test_user"
        )
        
        # Get length
        length = feature.get_length()
        
        # Check length (end - start + 1)
        self.assertEqual(length, 43125483 - 43044295 + 1)
        
    def test_add_child(self):
        """Test adding a child feature."""
        feature = Feature(
            name="BRCA1",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=43044295,
            end=43125483,
            genome_id=uuid.uuid4(),
            created_by="test_user"
        )
        
        # Add a child
        child_id = uuid.uuid4()
        feature.add_child(child_id)
        
        # Check that the child was added
        self.assertIn(child_id, feature.child_ids)
        self.assertEqual(len(feature.child_ids), 1)
        
        # Add the same child again (should not duplicate)
        feature.add_child(child_id)
        self.assertEqual(len(feature.child_ids), 1)
        
        # Add another child
        another_child_id = uuid.uuid4()
        feature.add_child(another_child_id)
        self.assertEqual(len(feature.child_ids), 2)
        
    def test_to_dict(self):
        """Test converting a feature to a dictionary."""
        genome_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        feature = Feature(
            name="BRCA1 Exon 1",
            feature_type=FeatureType.EXON,
            chromosome="chr17",
            start=43044295,
            end=43045679,
            genome_id=genome_id,
            created_by="test_user",
            strand="+",
            parent_id=parent_id
        )
        
        # Add a child
        child_id = uuid.uuid4()
        feature.add_child(child_id)
        
        # Convert to dictionary
        feature_dict = feature.to_dict()
        
        # Check dictionary values
        self.assertEqual(feature_dict["name"], "BRCA1 Exon 1")
        self.assertEqual(feature_dict["feature_type"], "EXON")
        self.assertEqual(feature_dict["chromosome"], "chr17")
        self.assertEqual(feature_dict["start"], 43044295)
        self.assertEqual(feature_dict["end"], 43045679)
        self.assertEqual(feature_dict["genome_id"], str(genome_id))
        self.assertEqual(feature_dict["created_by"], "test_user")
        self.assertEqual(feature_dict["strand"], "+")
        self.assertEqual(feature_dict["parent_id"], str(parent_id))
        self.assertEqual(feature_dict["child_ids"], [str(child_id)])
        self.assertIn("id", feature_dict)
        self.assertIn("created_at", feature_dict)


class TestGenomeRepository(unittest.TestCase):
    """Test cases for the GenomeRepository."""
    
    def setUp(self):
        """Set up test case."""
        self.repo = GenomeRepository()
        
    def test_create_and_get_genome(self):
        """Test creating and retrieving a genome."""
        # Create a genome
        genome = Genome(
            name="Human Genome",
            species="Homo sapiens",
            assembly_version="GRCh38",
            created_by="test_user"
        )
        
        # Store in repository
        stored_genome = self.repo.create_genome(genome)
        
        # Retrieve from repository
        retrieved_genome = self.repo.get_genome(genome.id)
        
        # Check that the genome was stored and retrieved correctly
        self.assertEqual(retrieved_genome.id, genome.id)
        self.assertEqual(retrieved_genome.name, "Human Genome")
        
    def test_get_all_genomes(self):
        """Test retrieving all genomes."""
        # Create and store genomes
        genome1 = Genome(
            name="Human Genome",
            species="Homo sapiens",
            assembly_version="GRCh38",
            created_by="test_user"
        )
        genome2 = Genome(
            name="Mouse Genome",
            species="Mus musculus",
            assembly_version="GRCm39",
            created_by="test_user"
        )
        
        self.repo.create_genome(genome1)
        self.repo.create_genome(genome2)
        
        # Get all genomes
        all_genomes = self.repo.get_all_genomes()
        
        # Check that both genomes were retrieved
        self.assertEqual(len(all_genomes), 2)
        self.assertTrue(any(g.name == "Human Genome" for g in all_genomes))
        self.assertTrue(any(g.name == "Mouse Genome" for g in all_genomes))
        
    def test_update_genome(self):
        """Test updating a genome."""
        # Create and store a genome
        genome = Genome(
            name="Human Genome",
            species="Homo sapiens",
            assembly_version="GRCh38",
            created_by="test_user"
        )
        self.repo.create_genome(genome)
        
        # Update the genome
        genome.name = "Updated Human Genome"
        genome.fasta_path = "/path/to/genome.fa"
        self.repo.update_genome(genome)
        
        # Retrieve and check the updated genome
        updated_genome = self.repo.get_genome(genome.id)
        self.assertEqual(updated_genome.name, "Updated Human Genome")
        self.assertEqual(updated_genome.fasta_path, "/path/to/genome.fa")
        
    def test_delete_genome(self):
        """Test deleting a genome."""
        # Create and store a genome
        genome = Genome(
            name="Human Genome",
            species="Homo sapiens",
            assembly_version="GRCh38",
            created_by="test_user"
        )
        self.repo.create_genome(genome)
        
        # Delete the genome
        result = self.repo.delete_genome(genome.id)
        
        # Check that the genome was deleted
        self.assertTrue(result)
        self.assertIsNone(self.repo.get_genome(genome.id))
        
        # Try deleting a non-existent genome
        result = self.repo.delete_genome(uuid.uuid4())
        self.assertFalse(result)
        
    def test_get_genomes_by_species(self):
        """Test retrieving genomes by species."""
        # Create and store genomes
        genome1 = Genome(
            name="Human Genome 1",
            species="Homo sapiens",
            assembly_version="GRCh38",
            created_by="test_user"
        )
        genome2 = Genome(
            name="Human Genome 2",
            species="Homo sapiens",
            assembly_version="GRCh37",
            created_by="test_user"
        )
        genome3 = Genome(
            name="Mouse Genome",
            species="Mus musculus",
            assembly_version="GRCm39",
            created_by="test_user"
        )
        
        self.repo.create_genome(genome1)
        self.repo.create_genome(genome2)
        self.repo.create_genome(genome3)
        
        # Get genomes by species
        human_genomes = self.repo.get_genomes_by_species("Homo sapiens")
        mouse_genomes = self.repo.get_genomes_by_species("Mus musculus")
        rat_genomes = self.repo.get_genomes_by_species("Rattus norvegicus")
        
        # Check results
        self.assertEqual(len(human_genomes), 2)
        self.assertEqual(len(mouse_genomes), 1)
        self.assertEqual(len(rat_genomes), 0)
        
    def test_get_genomes_by_assembly(self):
        """Test retrieving genomes by assembly version."""
        # Create and store genomes
        genome1 = Genome(
            name="Human Genome GRCh38",
            species="Homo sapiens",
            assembly_version="GRCh38",
            created_by="test_user"
        )
        genome2 = Genome(
            name="Human Genome GRCh37",
            species="Homo sapiens",
            assembly_version="GRCh37",
            created_by="test_user"
        )
        
        self.repo.create_genome(genome1)
        self.repo.create_genome(genome2)
        
        # Get genomes by assembly
        grch38_genomes = self.repo.get_genomes_by_assembly("GRCh38")
        grch37_genomes = self.repo.get_genomes_by_assembly("GRCh37")
        grch36_genomes = self.repo.get_genomes_by_assembly("GRCh36")
        
        # Check results
        self.assertEqual(len(grch38_genomes), 1)
        self.assertEqual(len(grch37_genomes), 1)
        self.assertEqual(len(grch36_genomes), 0)


class TestFeatureRepository(unittest.TestCase):
    """Test cases for the FeatureRepository."""
    
    def setUp(self):
        """Set up test case."""
        self.repo = FeatureRepository()
        self.genome_id = uuid.uuid4()
        
    def test_create_and_get_feature(self):
        """Test creating and retrieving a feature."""
        # Create a feature
        feature = Feature(
            name="BRCA1",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=43044295,
            end=43125483,
            genome_id=self.genome_id,
            created_by="test_user"
        )
        
        # Store in repository
        stored_feature = self.repo.create_feature(feature)
        
        # Retrieve from repository
        retrieved_feature = self.repo.get_feature(feature.id)
        
        # Check that the feature was stored and retrieved correctly
        self.assertEqual(retrieved_feature.id, feature.id)
        self.assertEqual(retrieved_feature.name, "BRCA1")
        
    def test_get_all_features(self):
        """Test retrieving all features."""
        # Create and store features
        feature1 = Feature(
            name="BRCA1",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=43044295,
            end=43125483,
            genome_id=self.genome_id,
            created_by="test_user"
        )
        feature2 = Feature(
            name="TP53",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=7668402,
            end=7687550,
            genome_id=self.genome_id,
            created_by="test_user"
        )
        
        self.repo.create_feature(feature1)
        self.repo.create_feature(feature2)
        
        # Get all features
        all_features = self.repo.get_all_features()
        
        # Check that both features were retrieved
        self.assertEqual(len(all_features), 2)
        self.assertTrue(any(f.name == "BRCA1" for f in all_features))
        self.assertTrue(any(f.name == "TP53" for f in all_features))
        
    def test_update_feature(self):
        """Test updating a feature."""
        # Create and store a feature
        feature = Feature(
            name="BRCA1",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=43044295,
            end=43125483,
            genome_id=self.genome_id,
            created_by="test_user"
        )
        self.repo.create_feature(feature)
        
        # Update the feature
        feature.name = "Updated BRCA1"
        feature.description = "Updated description"
        self.repo.update_feature(feature)
        
        # Retrieve and check the updated feature
        updated_feature = self.repo.get_feature(feature.id)
        self.assertEqual(updated_feature.name, "Updated BRCA1")
        self.assertEqual(updated_feature.description, "Updated description")
        
    def test_delete_feature(self):
        """Test deleting a feature."""
        # Create and store a feature
        feature = Feature(
            name="BRCA1",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=43044295,
            end=43125483,
            genome_id=self.genome_id,
            created_by="test_user"
        )
        self.repo.create_feature(feature)
        
        # Delete the feature
        result = self.repo.delete_feature(feature.id)
        
        # Check that the feature was deleted
        self.assertTrue(result)
        self.assertIsNone(self.repo.get_feature(feature.id))
        
        # Try deleting a non-existent feature
        result = self.repo.delete_feature(uuid.uuid4())
        self.assertFalse(result)
        
    def test_get_features_by_genome(self):
        """Test retrieving features by genome."""
        # Create genomes
        genome1_id = uuid.uuid4()
        genome2_id = uuid.uuid4()
        
        # Create features for different genomes
        feature1 = Feature(
            name="Human BRCA1",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=43044295,
            end=43125483,
            genome_id=genome1_id,
            created_by="test_user"
        )
        feature2 = Feature(
            name="Human TP53",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=7668402,
            end=7687550,
            genome_id=genome1_id,
            created_by="test_user"
        )
        feature3 = Feature(
            name="Mouse Brca1",
            feature_type=FeatureType.GENE,
            chromosome="chr11",
            start=101154456,
            end=101228723,
            genome_id=genome2_id,
            created_by="test_user"
        )
        
        self.repo.create_feature(feature1)
        self.repo.create_feature(feature2)
        self.repo.create_feature(feature3)
        
        # Get features by genome
        genome1_features = self.repo.get_features_by_genome(genome1_id)
        genome2_features = self.repo.get_features_by_genome(genome2_id)
        
        # Check results
        self.assertEqual(len(genome1_features), 2)
        self.assertEqual(len(genome2_features), 1)
        
    def test_get_features_by_type(self):
        """Test retrieving features by type."""
        # Create features of different types
        gene_feature = Feature(
            name="BRCA1",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=43044295,
            end=43125483,
            genome_id=self.genome_id,
            created_by="test_user"
        )
        exon_feature = Feature(
            name="BRCA1 Exon 1",
            feature_type=FeatureType.EXON,
            chromosome="chr17",
            start=43044295,
            end=43045679,
            genome_id=self.genome_id,
            created_by="test_user"
        )
        snp_feature = Feature(
            name="rs28897672",
            feature_type=FeatureType.SNP,
            chromosome="chr17",
            start=43094365,
            end=43094365,
            genome_id=self.genome_id,
            created_by="test_user"
        )
        
        self.repo.create_feature(gene_feature)
        self.repo.create_feature(exon_feature)
        self.repo.create_feature(snp_feature)
        
        # Get features by type
        gene_features = self.repo.get_features_by_type(FeatureType.GENE)
        exon_features = self.repo.get_features_by_type(FeatureType.EXON)
        snp_features = self.repo.get_features_by_type(FeatureType.SNP)
        regulatory_features = self.repo.get_features_by_type(FeatureType.REGULATORY)
        
        # Check results
        self.assertEqual(len(gene_features), 1)
        self.assertEqual(len(exon_features), 1)
        self.assertEqual(len(snp_features), 1)
        self.assertEqual(len(regulatory_features), 0)
        
        # Also check using string type
        gene_features_str = self.repo.get_features_by_type("GENE")
        self.assertEqual(len(gene_features_str), 1)
        
        # Check with genome filter
        gene_features_genome = self.repo.get_features_by_type(FeatureType.GENE, self.genome_id)
        self.assertEqual(len(gene_features_genome), 1)
        
    def test_get_features_by_chromosome(self):
        """Test retrieving features by chromosome."""
        # Create features on different chromosomes
        feature1 = Feature(
            name="BRCA1",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=43044295,
            end=43125483,
            genome_id=self.genome_id,
            created_by="test_user"
        )
        feature2 = Feature(
            name="TP53",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=7668402,
            end=7687550,
            genome_id=self.genome_id,
            created_by="test_user"
        )
        feature3 = Feature(
            name="BRCA2",
            feature_type=FeatureType.GENE,
            chromosome="chr13",
            start=32315510,
            end=32400268,
            genome_id=self.genome_id,
            created_by="test_user"
        )
        
        self.repo.create_feature(feature1)
        self.repo.create_feature(feature2)
        self.repo.create_feature(feature3)
        
        # Get features by chromosome
        chr17_features = self.repo.get_features_by_chromosome("chr17", self.genome_id)
        chr13_features = self.repo.get_features_by_chromosome("chr13", self.genome_id)
        chr1_features = self.repo.get_features_by_chromosome("chr1", self.genome_id)
        
        # Check results
        self.assertEqual(len(chr17_features), 2)
        self.assertEqual(len(chr13_features), 1)
        self.assertEqual(len(chr1_features), 0)
        
    def test_get_features_in_region(self):
        """Test retrieving features in a genomic region."""
        # Create features
        feature1 = Feature(
            name="BRCA1",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=43044295,
            end=43125483,
            genome_id=self.genome_id,
            created_by="test_user"
        )
        feature2 = Feature(
            name="TP53",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=7668402,
            end=7687550,
            genome_id=self.genome_id,
            created_by="test_user"
        )
        
        self.repo.create_feature(feature1)
        self.repo.create_feature(feature2)
        
        # Get features in regions
        brca1_region = self.repo.get_features_in_region("chr17", 43044000, 43126000, self.genome_id)
        tp53_region = self.repo.get_features_in_region("chr17", 7668000, 7688000, self.genome_id)
        no_feature_region = self.repo.get_features_in_region("chr17", 10000000, 20000000, self.genome_id)
        
        # Check results
        self.assertEqual(len(brca1_region), 1)
        self.assertEqual(brca1_region[0].name, "BRCA1")
        self.assertEqual(len(tp53_region), 1)
        self.assertEqual(tp53_region[0].name, "TP53")
        self.assertEqual(len(no_feature_region), 0)
        
    def test_get_features_by_parent(self):
        """Test retrieving child features of a parent feature."""
        # Create parent feature
        parent = Feature(
            name="BRCA1",
            feature_type=FeatureType.GENE,
            chromosome="chr17",
            start=43044295,
            end=43125483,
            genome_id=self.genome_id,
            created_by="test_user"
        )
        self.repo.create_feature(parent)
        
        # Create child features
        child1 = Feature(
            name="BRCA1 Exon 1",
            feature_type=FeatureType.EXON,
            chromosome="chr17",
            start=43044295,
            end=43045679,
            genome_id=self.genome_id,
            created_by="test_user",
            parent_id=parent.id
        )
        child2 = Feature(
            name="BRCA1 Exon 2",
            feature_type=FeatureType.EXON,
            chromosome="chr17",
            start=43047680,
            end=43049111,
            genome_id=self.genome_id,
            created_by="test_user",
            parent_id=parent.id
        )
        
        self.repo.create_feature(child1)
        self.repo.create_feature(child2)
        
        # Get children by parent
        children = self.repo.get_features_by_parent(parent.id)
        
        # Check results
        self.assertEqual(len(children), 2)
        self.assertTrue(any(c.name == "BRCA1 Exon 1" for c in children))
        self.assertTrue(any(c.name == "BRCA1 Exon 2" for c in children))


class TestGenomeService(unittest.TestCase):
    """Test cases for the GenomeService."""
    
    def setUp(self):
        """Set up test case."""
        self.genome_repo = GenomeRepository()
        self.feature_repo = FeatureRepository()
        self.sample_repo = SampleRepository()
        self.sample_service = SampleService(self.sample_repo)
        self.service = GenomeService(
            self.genome_repo,
            self.feature_repo,
            self.sample_service
        )
        
        # Create a test sample
        self.sample = Sample(
            name="Test Sample",
            sample_type="blood",
            created_by="test_user"
        )
        self.sample_service.create_sample(self.sample)
        
    def test_create_genome(self):
        """Test creating a genome through the service."""
        # Create genome data
        genome_data = {
            "name": "Human Genome",
            "species": "Homo sapiens",
            "assembly_version": "GRCh38",
            "created_by": "test_user",
            "fasta_path": "/path/to/genome.fa",
            "sample_id": str(self.sample.id)
        }
        
        # Create genome
        genome = self.service.create_genome(genome_data)
        
        # Check genome
        self.assertEqual(genome.name, "Human Genome")
        self.assertEqual(genome.species, "Homo sapiens")
        self.assertEqual(genome.fasta_path, "/path/to/genome.fa")
        
        # Check that genome was added to sample
        updated_sample = self.sample_service.get_sample(self.sample.id)
        self.assertEqual(len(updated_sample.genome_ids), 1)
        self.assertEqual(str(updated_sample.genome_ids[0]), str(genome.id))
        
        # Test missing required field
        with self.assertRaises(ValueError):
            self.service.create_genome({
                "name": "Missing Fields Genome",
                "created_by": "test_user"
            })
        
    def test_create_feature(self):
        """Test creating a feature through the service."""
        # Create a genome first
        genome_data = {
            "name": "Human Genome",
            "species": "Homo sapiens",
            "assembly_version": "GRCh38",
            "created_by": "test_user"
        }
        genome = self.service.create_genome(genome_data)
        
        # Create feature data
        feature_data = {
            "name": "BRCA1",
            "feature_type": "GENE",
            "chromosome": "chr17",
            "start": 43044295,
            "end": 43125483,
            "genome_id": str(genome.id),
            "created_by": "test_user",
            "strand": "+"
        }
        
        # Create feature
        feature = self.service.create_feature(feature_data)
        
        # Check feature
        self.assertEqual(feature.name, "BRCA1")
        self.assertEqual(feature.feature_type, FeatureType.GENE)
        self.assertEqual(feature.chromosome, "chr17")
        
        # Check that feature was added to genome
        updated_genome = self.service.get_genome(genome.id)
        self.assertEqual(len(updated_genome.feature_ids), 1)
        self.assertEqual(str(updated_genome.feature_ids[0]), str(feature.id))
        
        # Create a child feature
        child_data = {
            "name": "BRCA1 Exon 1",
            "feature_type": "EXON",
            "chromosome": "chr17",
            "start": 43044295,
            "end": 43045679,
            "genome_id": str(genome.id),
            "created_by": "test_user",
            "parent_id": str(feature.id)
        }
        
        # Create child feature
        child = self.service.create_feature(child_data)
        
        # Check that child was linked to parent
        parent = self.service.get_feature(feature.id)
        self.assertEqual(len(parent.child_ids), 1)
        self.assertEqual(str(parent.child_ids[0]), str(child.id))
        
        # Test missing required field
        with self.assertRaises(ValueError):
            self.service.create_feature({
                "name": "Missing Fields Feature",
                "created_by": "test_user"
            })
        
        # Test invalid genome ID
        with self.assertRaises(ValueError):
            self.service.create_feature({
                "name": "Invalid Genome Feature",
                "feature_type": "GENE",
                "chromosome": "chr17",
                "start": 1000,
                "end": 2000,
                "genome_id": str(uuid.uuid4()),  # Random, non-existent genome ID
                "created_by": "test_user"
            })
            
    def test_get_genome_features(self):
        """Test getting all features for a genome."""
        # Create a genome
        genome_data = {
            "name": "Human Genome",
            "species": "Homo sapiens",
            "assembly_version": "GRCh38",
            "created_by": "test_user"
        }
        genome = self.service.create_genome(genome_data)
        
        # Create features
        feature1_data = {
            "name": "BRCA1",
            "feature_type": "GENE",
            "chromosome": "chr17",
            "start": 43044295,
            "end": 43125483,
            "genome_id": str(genome.id),
            "created_by": "test_user"
        }
        feature2_data = {
            "name": "TP53",
            "feature_type": "GENE",
            "chromosome": "chr17",
            "start": 7668402,
            "end": 7687550,
            "genome_id": str(genome.id),
            "created_by": "test_user"
        }
        
        self.service.create_feature(feature1_data)
        self.service.create_feature(feature2_data)
        
        # Get features for the genome
        features = self.service.get_genome_features(genome.id)
        
        # Check features
        self.assertEqual(len(features), 2)
        self.assertTrue(any(f.name == "BRCA1" for f in features))
        self.assertTrue(any(f.name == "TP53" for f in features))
        
    def test_get_features_in_region(self):
        """Test getting features in a genomic region."""
        # Create a genome
        genome_data = {
            "name": "Human Genome",
            "species": "Homo sapiens",
            "assembly_version": "GRCh38",
            "created_by": "test_user"
        }
        genome = self.service.create_genome(genome_data)
        
        # Create features
        feature1_data = {
            "name": "BRCA1",
            "feature_type": "GENE",
            "chromosome": "chr17",
            "start": 43044295,
            "end": 43125483,
            "genome_id": str(genome.id),
            "created_by": "test_user"
        }
        feature2_data = {
            "name": "TP53",
            "feature_type": "GENE",
            "chromosome": "chr17",
            "start": 7668402,
            "end": 7687550,
            "genome_id": str(genome.id),
            "created_by": "test_user"
        }
        
        self.service.create_feature(feature1_data)
        self.service.create_feature(feature2_data)
        
        # Get features in BRCA1 region
        brca1_region = self.service.get_features_in_region(
            genome.id, "chr17", 43044000, 43126000
        )
        
        # Check results
        self.assertEqual(len(brca1_region), 1)
        self.assertEqual(brca1_region[0].name, "BRCA1")
        
    def test_get_feature_hierarchy(self):
        """Test getting feature hierarchy."""
        # Create a genome
        genome_data = {
            "name": "Human Genome",
            "species": "Homo sapiens",
            "assembly_version": "GRCh38",
            "created_by": "test_user"
        }
        genome = self.service.create_genome(genome_data)
        
        # Create parent feature
        parent_data = {
            "name": "BRCA1",
            "feature_type": "GENE",
            "chromosome": "chr17",
            "start": 43044295,
            "end": 43125483,
            "genome_id": str(genome.id),
            "created_by": "test_user"
        }
        parent = self.service.create_feature(parent_data)
        
        # Create child features
        child1_data = {
            "name": "BRCA1 Exon 1",
            "feature_type": "EXON",
            "chromosome": "chr17",
            "start": 43044295,
            "end": 43045679,
            "genome_id": str(genome.id),
            "created_by": "test_user",
            "parent_id": str(parent.id)
        }
        child2_data = {
            "name": "BRCA1 Exon 2",
            "feature_type": "EXON",
            "chromosome": "chr17",
            "start": 43047680,
            "end": 43049111,
            "genome_id": str(genome.id),
            "created_by": "test_user",
            "parent_id": str(parent.id)
        }
        
        self.service.create_feature(child1_data)
        self.service.create_feature(child2_data)
        
        # Get hierarchy
        hierarchy = self.service.get_feature_hierarchy(parent.id)
        
        # Check hierarchy
        self.assertEqual(hierarchy["name"], "BRCA1")
        self.assertEqual(len(hierarchy["children"]), 2)
        self.assertTrue(any(c["name"] == "BRCA1 Exon 1" for c in hierarchy["children"]))
        self.assertTrue(any(c["name"] == "BRCA1 Exon 2" for c in hierarchy["children"]))
        
    def test_delete_genome_cascades_to_features(self):
        """Test that deleting a genome also deletes its features."""
        # Create a genome
        genome_data = {
            "name": "Human Genome",
            "species": "Homo sapiens",
            "assembly_version": "GRCh38",
            "created_by": "test_user"
        }
        genome = self.service.create_genome(genome_data)
        
        # Create features
        feature1_data = {
            "name": "BRCA1",
            "feature_type": "GENE",
            "chromosome": "chr17",
            "start": 43044295,
            "end": 43125483,
            "genome_id": str(genome.id),
            "created_by": "test_user"
        }
        feature2_data = {
            "name": "TP53",
            "feature_type": "GENE",
            "chromosome": "chr17",
            "start": 7668402,
            "end": 7687550,
            "genome_id": str(genome.id),
            "created_by": "test_user"
        }
        
        feature1 = self.service.create_feature(feature1_data)
        feature2 = self.service.create_feature(feature2_data)
        
        # Delete the genome
        self.service.delete_genome(genome.id)
        
        # Check that features were deleted
        self.assertIsNone(self.service.get_feature(feature1.id))
        self.assertIsNone(self.service.get_feature(feature2.id))


if __name__ == '__main__':
    unittest.main()