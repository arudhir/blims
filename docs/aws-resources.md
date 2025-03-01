# AWS Resources Created by BLIMS

This document details the AWS resources created when you deploy the BLIMS infrastructure, their purpose, estimated costs, and how they work together.

## Resource Overview

BLIMS creates the following AWS resources:

### VPC & Networking

| Resource | Description | Approximate Cost |
|----------|-------------|------------------|
| VPC | Virtual Private Cloud network isolation | Free |
| Subnets (4) | 2 public and 2 private subnets across availability zones | Free |
| NAT Gateway | Allows outbound internet from private subnets | $32/month + data transfer |
| Internet Gateway | Allows inbound/outbound internet for public subnets | Free |
| Route Tables | Network routing rules | Free |
| Security Group | Firewall rules for Batch compute environment | Free |

### Storage

| Resource | Description | Approximate Cost |
|----------|-------------|------------------|
| S3 Bioinformatics Bucket | Stores sequencing data and analysis results | $0.023/GB/month |
| S3 Application Bucket | Stores application configs and assets | $0.023/GB/month |
| DynamoDB Table | Stores sample metadata and relationships | Pay-per-request, starts at $0 |

### Compute

| Resource | Description | Approximate Cost |
|----------|-------------|------------------|
| Batch Compute Environment | Auto-scaling EC2 environment for bioinformatics jobs | $0 when idle |
| EC2 Instances | Compute instances for bioinformatics (auto-scaled) | $0.04-$0.10/hour per vCPU |
| Batch Job Queue | Queue for processing bioinformatics job requests | Free |
| Batch Job Definitions | Pre-configured bioinformatics tools | Free |

### Security & IAM

| Resource | Description | Approximate Cost |
|----------|-------------|------------------|
| IAM Roles (3) | Service roles for Batch, EC2, and jobs | Free |
| IAM Policies | Permissions policies for the roles | Free |
| Instance Profile | Links IAM roles to EC2 instances | Free |

## Cost Analysis

### Fixed Costs (24/7)

These resources incur charges regardless of usage:

- **NAT Gateway**: ~$32/month
- **S3 Standard Storage**: $0.023/GB/month
- **Management & Governance**: Minimal CloudFormation charges

### Variable Costs (Pay-per-use)

These resources only incur charges when used:

- **EC2 Instances**: Only charged when analysis jobs are running
- **Data Transfer**: $0.09/GB for outbound data
- **DynamoDB**: Pay for read/write capacity and storage used

### Example Cost Scenarios

1. **Development/Testing Environment**
   - Fixed costs: ~$35/month
   - Minimal usage: ~$5-10/month
   - Total: ~$40-45/month

2. **Small Research Lab**
   - Fixed costs: ~$35/month
   - 5TB sequencing data: ~$115/month
   - Moderate compute: ~$50/month
   - Total: ~$200/month

3. **Production Genomics Facility**
   - Fixed costs: ~$35/month
   - 50TB sequencing data: ~$1,150/month
   - Heavy compute: ~$500-1,000/month
   - Total: ~$1,700-2,200/month

### Cost Optimization

1. **Reduce NAT Gateway Costs**
   - Use spot instances in the compute environment
   - Delete the NAT Gateway when not in use

2. **Optimize Storage Costs**
   - S3 lifecycle rules automatically move older data to cheaper storage
   - Consider Glacier for long-term archival

3. **Batch Optimization**
   - The compute environment scales to zero when idle
   - Use spot instances for non-critical workloads

## Resource Details

### VPC Configuration

```yaml
VPC:
  CIDR: 10.0.0.0/16
  EnableDnsSupport: true
  EnableDnsHostnames: true

Subnets:
  PublicSubnet1: 10.0.0.0/24 (AZ: us-east-1a)
  PublicSubnet2: 10.0.1.0/24 (AZ: us-east-1b)
  PrivateSubnet1: 10.0.2.0/24 (AZ: us-east-1a)
  PrivateSubnet2: 10.0.3.0/24 (AZ: us-east-1b)
```

### Batch Compute Environment

```yaml
BatchComputeEnvironment:
  Type: MANAGED
  State: ENABLED
  ComputeResources:
    Type: EC2
    MinvCpus: 0
    MaxvCpus: 16
    DesiredvCpus: 0
    InstanceTypes:
      - c5
      - m5
```

### S3 Bucket Configuration

```yaml
BioinformaticsBucket:
  VersioningConfiguration:
    Status: Enabled
  LifecycleConfiguration:
    Rules:
      - TransitionToInfrequentAccess: 90 days
```

### DynamoDB Configuration

```yaml
SamplesTable:
  BillingMode: PAY_PER_REQUEST
  KeySchema:
    - AttributeName: sample_id
      KeyType: HASH
```

## Architecture Diagram

```
                                     ┌─────────────────┐
                                     │                 │
                                     │ Internet        │
                                     │                 │
                                     └────────┬────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ VPC                     ┌─────────────┐                                 │
│                         │ Internet    │                                 │
│                         │ Gateway     │                                 │
│                         └──────┬──────┘                                 │
│                                │                                        │
│ ┌──────────────┐  ┌────────────▼───────────┐   ┌───────────────┐       │
│ │              │  │                        │   │               │       │
│ │ Public       │  │ Public                 │   │ NAT Gateway   │       │
│ │ Subnet 1     ├──► Subnet 2               ├───►               │       │
│ │              │  │                        │   │               │       │
│ └──────────────┘  └────────────────────────┘   └───────┬───────┘       │
│                                                        │               │
│                                                        ▼               │
│ ┌──────────────┐  ┌────────────────────────┐                           │
│ │              │  │                        │                           │
│ │ Private      │  │ Private                │                           │
│ │ Subnet 1     │  │ Subnet 2               │                           │
│ │ (Batch/EC2)  │  │                        │                           │
│ └──────┬───────┘  └────────────────────────┘                           │
│        │                                                               │
└────────┼───────────────────────────────────────────────────────────────┘
         │
         │                   ┌───────────────┐     ┌───────────────┐
         │                   │               │     │               │
         └──────────────────►│ AWS Batch     │────►│ EC2 Instances │
                             │ Job Queue     │     │               │
                             │               │     │               │
                             └───────┬───────┘     └───────────────┘
                                     │
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
          ┌─────────▼──────┐ ┌───────▼────────┐ ┌────▼───────────┐
          │                │ │                │ │                │
          │ S3 Buckets     │ │ DynamoDB       │ │ Job Definition │
          │                │ │                │ │                │
          └────────────────┘ └────────────────┘ └────────────────┘
```

## Deployment Process

1. VPC Stack Deployment:
   - Creates the networking infrastructure
   - Takes ~5-10 minutes to complete

2. Main Stack Deployment:
   - Creates storage, compute, and IAM resources
   - Takes ~10-15 minutes to complete

3. Configuration Generation:
   - Generates `config/aws_config.json` with resource information
   - Used by BLIMS application to connect to AWS resources

## Cloud Security Considerations

- All IAM roles follow least-privilege principle
- S3 buckets use versioning to protect against accidental deletion
- No public access to resources by default
- DynamoDB uses encryption at rest
- Networking is properly segmented with private subnets

## AWS Console Locations

After deployment, you can find your resources in the AWS Console:

- **CloudFormation**: https://console.aws.amazon.com/cloudformation
- **VPC**: https://console.aws.amazon.com/vpc
- **S3**: https://console.aws.amazon.com/s3
- **DynamoDB**: https://console.aws.amazon.com/dynamodb
- **Batch**: https://console.aws.amazon.com/batch
- **IAM**: https://console.aws.amazon.com/iam