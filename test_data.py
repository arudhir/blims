"""Test data generator for BLIMS."""

from uuid import UUID
from blims.core.service import SampleService
from blims.models.sample import Sample, reset_sample_counter

def create_test_data(service: SampleService):
    """Create test data for the BLIMS application.
    
    This function creates 5 samples with relationships:
    - 2 parent-child relationships
    - 1 container relationship
    
    Args:
        service: The sample service to use for creating samples
    """
    # Check if we already have samples (to avoid duplicates)
    if service.repository.get_all():
        return
    
    # Reset sample counter to ensure we start from s1
    reset_sample_counter(0)
    
    # Create base samples
    blood_sample = service.create_sample(
        name="Blood Sample A",
        sample_type="Blood",
        created_by="System",
        metadata={
            "source": "Patient 12345",
            "collection_date": "2025-02-28",
            "volume_ml": 5,
            "test_data": True
        },
        barcode="BLOOD001"
    )
    
    tissue_sample = service.create_sample(
        name="Tissue Sample B",
        sample_type="Tissue",
        created_by="System",
        metadata={
            "source": "Patient 67890",
            "collection_date": "2025-02-27",
            "tissue_type": "Liver",
            "test_data": True
        },
        barcode="TISSUE001"
    )
    
    # Create a derived sample from blood
    dna_sample = service.derive_sample(
        parent_id=blood_sample.id,
        name="DNA Extract from Sample A",
        sample_type="DNA",
        created_by="System",
        metadata={
            "extraction_method": "Column",
            "concentration_ng_ul": 25.6,
            "test_data": True
        },
        barcode="DNA001"
    )
    
    # Create a container
    plate_sample = service.create_sample(
        name="96-well Plate X",
        sample_type="Plate",
        created_by="System",
        metadata={
            "plate_type": "96-well PCR",
            "manufacturer": "LabCorp",
            "test_data": True
        },
        barcode="PLATE001",
        is_container=True
    )
    
    # Create another container (Box)
    box_sample = service.create_sample(
        name="Sample Storage Box Y",
        sample_type="Box",
        created_by="System",
        metadata={
            "box_type": "Freezer Box",
            "capacity": "81 tubes",
            "test_data": True
        },
        barcode="BOX001",
        is_container=True
    )
    
    # Create a sample to be contained
    pcr_sample = service.create_sample(
        name="PCR Product C",
        sample_type="PCR",
        created_by="System",
        metadata={
            "primer_set": "16S-V4",
            "cycles": 30,
            "test_data": True
        },
        barcode="PCR001"
    )
    
    # Add PCR sample to the plate
    service.add_sample_to_container(pcr_sample.id, plate_sample.id)
    
    # Add plate to the box (container inside container)
    service.add_sample_to_container(plate_sample.id, box_sample.id)
    
    # Add some files to samples
    service.add_file_to_sample(dna_sample.id, "/data/sequencing/dna_sample_qc.pdf")
    service.add_file_to_sample(pcr_sample.id, "/data/pcr/gel_image.png")
    
    # Add additional metadata
    service.add_metadata_to_sample(blood_sample.id, "stored_at", "-80C")
    service.add_metadata_to_sample(tissue_sample.id, "fixation", "Formalin")
    
    # Print with the sample_id
    print(f"Created test samples:")
    print(f"  - {blood_sample.sample_id}: {blood_sample.name} (Barcode: {blood_sample.barcode})")
    print(f"  - {tissue_sample.sample_id}: {tissue_sample.name} (Barcode: {tissue_sample.barcode})")
    print(f"  - {dna_sample.sample_id}: {dna_sample.name} (Barcode: {dna_sample.barcode})")
    print(f"  - {plate_sample.sample_id}: {plate_sample.name} (Barcode: {plate_sample.barcode}) [Container]")
    print(f"  - {box_sample.sample_id}: {box_sample.name} (Barcode: {box_sample.barcode}) [Container]")
    print(f"  - {pcr_sample.sample_id}: {pcr_sample.name} (Barcode: {pcr_sample.barcode})")
    print(f"Container relationships:")
    print(f"  - {pcr_sample.sample_id} is contained in {plate_sample.sample_id}")
    print(f"  - {plate_sample.sample_id} is contained in {box_sample.sample_id}")

if __name__ == "__main__":
    # This allows running the script directly to create test data
    service = SampleService()
    create_test_data(service)
    print("Test data creation complete.")