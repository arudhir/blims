# BLIMS Quick Start Guide

This guide will help you get up and running with BLIMS quickly, covering local development, Docker deployment, and AWS cloud deployment.

## Prerequisites

- Python 3.11 or later
- Docker and Docker Compose (optional, for containerized deployment)
- AWS CLI configured with appropriate credentials (optional, for AWS deployment)
- Git

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/blims.git
cd blims
```

### 2. Set Up the Environment

```bash
# Create and set up the environment with all dependencies
make setup
```

This will:
- Create a Python virtual environment
- Install all required dependencies
- Set up development tools

### 3. Create Test Data

```bash
# Generate sample test data
make test-data
```

This creates:
- Sample records with metadata
- Parent-child relationships
- Container hierarchies
- Sample barcodes

### 4. Run the Application

```bash
# Start both API and UI in development mode
make dev
```

### 5. Access the Application

- **UI**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs

## Docker Deployment

### 1. Build and Start Containers

```bash
# Build and start all services
make docker-dev
```

This builds and starts:
- API container on port 8000
- UI container on port 8501

### 2. Access the Containerized Application

- **UI**: http://localhost:8501
- **API Docs**: http://localhost:8000/docs

### 3. Stop the Containers

```bash
# Stop all containers
make docker-down
```

## AWS Cloud Deployment

### 1. Validate AWS Templates

```bash
# Validate CloudFormation templates without deploying
make aws-validate
```

### 2. Deploy AWS Infrastructure

```bash
# Deploy the full AWS infrastructure
make aws-deploy
```

This creates:
- VPC with networking
- S3 buckets for data storage
- DynamoDB for metadata
- AWS Batch for analysis jobs

### 3. Update Application Configuration

The deployment process automatically generates a configuration file at `config/aws_config.json` with information about the created resources. The application will use this file to connect to AWS.

### 4. Deploy the Application

After AWS infrastructure is set up, you can deploy the application:

```bash
# Build with AWS configuration
make docker-build

# Deploy to your preferred container service (ECS, EKS, etc.)
# This will depend on your specific deployment strategy
```

## Basic Usage

### Sample Management

1. **Create Samples:**
   - Navigate to "Create Sample" in the UI
   - Fill in sample details, including name, type, and metadata
   - Create biological samples or containers

2. **View Samples:**
   - The dashboard shows all samples and their relationships
   - Use the interactive network visualization to explore relationships

3. **Manage Containers:**
   - Create container samples (plates, boxes, etc.)
   - Add samples to containers
   - View container hierarchies

### Bioinformatics (with AWS)

1. **Upload Sequencing Data:**
   - Use the API to upload FASTQ, BAM, or other sequencing files
   - Data is stored in S3

2. **Submit Analyses:**
   - Select samples and analysis types
   - Submit jobs to AWS Batch
   - Monitor progress

3. **View Results:**
   - Access analysis results
   - Download result files
   - Link results to samples

## Common Operations

### Running Tests

```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Generate coverage report
make coverage
```

### Code Quality

```bash
# Format code
make format

# Check code style
make check

# Run linters
make lint

# Do all formatting and linting
make reformat
```

### Viewing Logs

```bash
# View Docker logs
make docker-logs
```

## Troubleshooting

### Common Issues

1. **Port Conflicts:**
   - If ports 8000 or 8501 are in use, modify them in the docker-compose.yml file

2. **AWS Deployment Failures:**
   - Check CloudFormation events in the AWS Console
   - Ensure your AWS CLI is configured correctly
   - Verify you have necessary permissions

3. **Database Connection Issues:**
   - Ensure DynamoDB table exists and is accessible
   - Check IAM permissions

### Getting Help

- Check the detailed documentation in the `docs/` directory
- Submit issues on GitHub
- Consult the API documentation at `/docs` endpoint