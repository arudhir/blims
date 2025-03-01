# BLIMS Bioinformatics Guide

This guide explains how to use BLIMS for bioinformatics data management and analysis workflows.

## Supported Data Types

BLIMS supports the following sequencing data types:

- **Illumina Short Reads**
  - FASTQ, FASTQ.GZ formats
  - Single-end and paired-end reads
  - Common Illumina applications (DNA-seq, RNA-seq, etc.)

- **Long Reads**
  - Oxford Nanopore Technologies (ONT) data
  - PacBio data
  - FAST5, FASTQ formats

- **Processed Data**
  - BAM/SAM alignment files
  - VCF variant files
  - FASTA assemblies

## Bioinformatics File Organization

BLIMS organizes bioinformatics data in a standard structure:

```
s3://blims-bioinformatics-{env}/
├── samples/
│   ├── s1/
│   │   ├── reads/
│   │   │   ├── illumina/
│   │   │   │   ├── sample_R1.fastq.gz
│   │   │   │   └── sample_R2.fastq.gz
│   │   │   └── nanopore/
│   │   │       └── sample.fast5
│   │   └── analyses/
│   │       ├── fastqc/
│   │       │   ├── sample_R1_fastqc.html
│   │       │   └── sample_R1_fastqc.zip
│   │       └── alignment/
│   │           └── sample.bam
│   └── s2/
│       └── ...
└── reference/
    └── genomes/
        └── hg38.fasta
```

## Uploading Sequencing Data

### Using the API

```python
from blims.utils.bioinformatics import get_bioinf_manager, SequencingType

# Get the bioinformatics manager
bioinf = get_bioinf_manager()

# Upload sequencing data
success, s3_key = bioinf.upload_reads(
    sample_id="s1",
    file_path="/path/to/sample_R1.fastq.gz",
    sequencing_type=SequencingType.ILLUMINA,
    metadata={
        "read_count": 1250000,
        "platform": "NextSeq",
        "run_id": "RUN123"
    }
)

if success:
    print(f"Data uploaded to {s3_key}")
```

### Using the Analysis Service

```python
from blims.core.analysis_service import AnalysisService

# Initialize the service
analysis_service = AnalysisService(repository=sample_repository)

# Upload sequencing data
data_info = analysis_service.upload_sequencing_data(
    sample_id="s1",
    file_path="/path/to/sample_R1.fastq.gz",
    sequencing_type="illumina",
    metadata={"read_count": 1250000}
)

print(f"Data uploaded: {data_info['s3_uri']}")
```

## Running Bioinformatics Analyses

BLIMS supports various bioinformatics analyses through AWS Batch. The system comes with pre-configured job definitions for common tools.

### Available Analysis Types

- **FastQC**: Quality control for sequencing data
- **BWA-MEM**: Sequence alignment
- **Custom Analyses**: Define your own analysis workflows

### Submitting an Analysis

```python
from blims.core.analysis_service import AnalysisService
from blims.utils.bioinformatics import AnalysisType

# Initialize the service
analysis_service = AnalysisService(repository=sample_repository)

# Submit a FastQC analysis
analysis = analysis_service.start_analysis(
    sample_id="s1",
    analysis_type=AnalysisType.FASTQC,
    analysis_name="QC for Sample 1",
    job_definition="arn:aws:batch:us-east-1:123456789012:job-definition/blims-fastqc-dev",
    parameters={
        "threads": "4",
        "additional_options": "--noextract"
    }
)

print(f"Analysis submitted, job ID: {analysis.job_id}")
```

### Checking Analysis Status

```python
# Check the status of an analysis
status = analysis_service.get_analysis_status(analysis.job_id)
print(f"Analysis status: {status.value}")
```

### Accessing Results

```python
# Get a URL for viewing results
url = analysis_service.get_analysis_result_url(
    sample_id="s1",
    analysis_id=analysis.id,
    file_name="sample_R1_fastqc.html"
)

print(f"Access results at: {url}")
```

## Custom Analysis Workflows

You can create custom analysis workflows by defining new job definitions in AWS Batch.

### Example: Custom RNA-Seq Analysis

1. **Create a Docker container with your tools**
2. **Register a job definition in AWS Batch**
3. **Add the job definition to your config**
4. **Submit the analysis:**

```python
analysis = analysis_service.start_analysis(
    sample_id="s1",
    analysis_type="rnaseq",
    analysis_name="RNA-Seq Analysis",
    job_definition="arn:aws:batch:us-east-1:123456789012:job-definition/custom-rnaseq",
    parameters={
        "reference": "s3://bucket/reference/genome.fa", 
        "gtf": "s3://bucket/reference/genes.gtf"
    }
)
```

## Managing Analysis Results

### Linking Results to Samples

Results are automatically linked to samples, and you can access them through the sample object:

```python
sample = repository.get(sample_id)

# Get all analyses for the sample
analyses = sample.get_analyses()

# Get FastQC analyses only
fastqc_analyses = sample.get_analyses(analysis_type="fastqc")

# Access analysis outputs
for analysis in analyses:
    if "output_files" in analysis:
        for file_info in analysis["output_files"]:
            print(f"Result file: {file_info['file_name']}")
```

### Result Visualization

The BLIMS UI provides visualization of analysis results, including:

- Interactive plots
- Quality reports
- File viewers

## Best Practices

1. **Standardize Sample IDs**: Use consistent naming for samples
2. **Include Metadata**: Add detailed metadata to sequencing data
3. **Group Related Analyses**: Use consistent analysis names for related jobs
4. **Monitor Storage Costs**: Regularly review S3 storage usage
5. **Use Job Parameters**: Pass parameters to jobs rather than hardcoding values

## Troubleshooting

### Common Analysis Issues

1. **Job Failure**: Check AWS Batch logs for error messages
2. **Missing Data**: Verify S3 paths and permissions
3. **Resource Limits**: Adjust job memory and CPU requirements

### Debugging Tips

1. Use the AWS Batch console to view job details
2. Check CloudWatch logs for detailed error messages
3. Verify IAM permissions for AWS Batch access
4. Test job definitions with small datasets first

## Reference

### Analysis Type Enum

```python
class AnalysisType(Enum):
    """Types of bioinformatics analyses."""
    
    FASTQC = "fastqc"
    ALIGNMENT = "alignment"
    VARIANT_CALLING = "variant-calling"
    ASSEMBLY = "assembly"
    TAXONOMIC_PROFILING = "taxonomic-profiling"
    RNA_SEQ = "rna-seq" 
    CUSTOM = "custom"
```

### Sequencing Type Enum

```python
class SequencingType(Enum):
    """Types of sequencing data."""
    
    ILLUMINA = "illumina"
    NANOPORE = "nanopore"
    PACBIO = "pacbio"
    OTHER = "other"
```

### File Type Enum

```python
class FileType(Enum):
    """Types of bioinformatics files."""
    
    FASTQ = "fastq"
    BAM = "bam"
    VCF = "vcf"
    FASTA = "fasta"
    BED = "bed"
    GFF = "gff"
    TSV = "tsv"
    HTML = "html"
    PDF = "pdf"
    OTHER = "other"
```