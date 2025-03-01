# BLIMS - Biolab Laboratory Information Management System

A modern, scalable system for managing laboratory samples, sequencing data, and bioinformatics analyses, designed for research labs and bioinformatics facilities.

![BLIMS Sample Network](https://raw.githubusercontent.com/yourusername/blims/main/docs/images/sample_network.png)

## Quick Start

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/blims.git
cd blims

# Set up the environment and dependencies
make setup

# Create test data
make test-data

# Start the development server
make dev

# Access the UI at http://localhost:8501
# Access the API at http://localhost:8000/docs
```

### Docker Deployment

```bash
# Build and start Docker containers
make docker-dev

# Access the UI at http://localhost:8501
# Access the API at http://localhost:8000/docs
```

## Features

- **Sample Management**
  - Track sample metadata, lineage, and relationships
  - Support for sample barcodes
  - Container organization (plates, boxes, racks)
  - Parent-child relationships for derived samples
  - Associate samples with reference genomes

- **Data Visualization**
  - Interactive sample network visualization
  - Container hierarchy views
  - Sample lineage tracking

- **Genomics Infrastructure**
  - Reference genome management with FASTA file support
  - Genomic feature tracking (genes, exons, variants, etc.)
  - Positional genomic data with chromosome and coordinate support
  - Hierarchical feature relationships (genes → exons)
  - Region-based feature queries

- **Bioinformatics Integration**
  - Sequencing data management
  - Analysis job submission to AWS Batch
  - Analysis results tracking and viewing
  - Support for common bioinformatics file formats
  - Complete RNA-Seq pipeline with automated processing stages

## Development Notes

### Project Structure

```
blims/
├── api/            # FastAPI routes and handlers
├── blims/          # Core package
│   ├── api/        # API implementation
│   ├── core/       # Business logic
│   ├── models/     # Data models (Sample, Genome, Feature, etc.)
│   ├── repositories/ # Data access layer
│   ├── services/   # Service layer with business logic
│   └── utils/      # Utilities
├── aws/            # AWS infrastructure
│   ├── batch/      # AWS Batch job definitions
│   ├── containers/ # Docker containers for pipeline stages
│   └── cfn/        # CloudFormation templates
├── tests/          # Test suite
├── streamlit_app.py # Streamlit UI
└── main.py         # FastAPI application
```

### Technology Stack

- **Backend**: Python 3.11+, FastAPI
- **Frontend**: Streamlit
- **Data Visualization**: Pyvis, NetworkX
- **Cloud Integration**: AWS (S3, DynamoDB, Batch)
- **Container**: Docker, Docker Compose
- **Development**: uv, pytest, black, flake8, mypy, isort

### Development Commands

```bash
# Code formatting and linting
make format      # Format code with black and isort
make check       # Check code style without modifying
make lint        # Run linters
make reformat    # Run format, check, and lint in sequence

# Testing
make test        # Run all tests
make test-unit   # Run only unit tests
make coverage    # Run tests with coverage report

# Application
make run         # Run the API application
make dev         # Run with auto-reload for development

# Docker
make docker-build  # Build Docker images
make docker-up     # Start containers
make docker-down   # Stop containers
make docker-logs   # View container logs
```

## AWS Integration

BLIMS can be deployed with AWS infrastructure for scalable bioinformatics processing.

### AWS Resources Created

When you deploy BLIMS to AWS, the following resources are created:

1. **Networking (VPC)**
   - VPC with public and private subnets in 2 availability zones
   - NAT Gateway for outbound internet access
   - Security groups for service access
   - Route tables configured for proper network isolation

2. **Storage**
   - S3 bucket for bioinformatics data (`blims-bioinformatics-{env}`)
   - S3 bucket for application assets (`blims-app-{env}`)
   - DynamoDB table for sample data (`blims-samples-{env}`)

3. **Compute**
   - AWS Batch compute environment with auto-scaling EC2 instances
   - AWS Batch job queue for bioinformatics job submission
   - Job definitions for common bioinformatics tools (FastQC, BWA-MEM)
   - Complete RNA-Seq pipeline with 6 processing stages:
     - Read processing (SRA tools, fastp, BBDuk)
     - Read normalization (BBNorm)
     - Transcript quantification (Salmon)
     - RNA assembly (SPAdes)
     - Annotation (TransDecoder, eggNOG)
     - Database integration (DuckDB)

4. **Security**
   - IAM roles with least-privilege permissions
   - Instance profiles for EC2 instances in the compute environment

### Deployment Commands

```bash
# Validate AWS CloudFormation templates (no resources created)
make aws-validate

# Deploy AWS infrastructure
make aws-deploy

# Interactive AWS deployment menu
make aws
```

### AWS Cost Considerations

The AWS resources created by BLIMS have the following estimated costs:

1. **Persistent Resources (24/7):**
   - NAT Gateway: ~$32/month
   - S3 buckets: $0.023 per GB/month (first 50 TB)
   - DynamoDB: Pay per use, starts at $0 with free tier

2. **On-Demand Resources (pay for what you use):**
   - AWS Batch/EC2: Configured to scale from 0-16 vCPUs, ~$0.04-$0.10/hour per vCPU
   - Data transfer: $0.09 per GB outbound (free inbound)

**Estimated Monthly Costs:**
- Minimum (infrastructure only): ~$35-45/month
- Typical small lab usage: ~$50-150/month
- Large-scale genomics: Costs scale with data volume and computation

**Cost Optimization Tips:**
- The infrastructure uses auto-scaling from 0 instances when idle
- S3 lifecycle rules transition data to cheaper storage after 90 days
- Delete the NAT Gateway when not in use to save ~$32/month

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests: `make test`
5. Format code: `make reformat`
6. Submit a pull request

## License

[MIT License](LICENSE)

---

## Contact

For questions or support, please open an issue on the GitHub repository.
