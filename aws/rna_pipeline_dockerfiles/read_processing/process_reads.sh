#!/bin/bash
set -e

# Required environment variables:
# SRA_ACCESSION - SRA accession number
# OUTPUT_BUCKET - S3 bucket for output
# OUTPUT_PREFIX - S3 prefix for output
# S3_REFERENCE_BUCKET - S3 bucket containing reference files
# RRNA_REFERENCE - Path to rRNA reference within reference bucket
# THREADS - Number of threads to use (default: 8)

echo "Starting RNA-Seq read processing pipeline"
echo "SRA Accession: ${SRA_ACCESSION}"
echo "Output bucket: ${OUTPUT_BUCKET}"
echo "Output prefix: ${OUTPUT_PREFIX}"

# Set defaults
THREADS=${THREADS:-8}
WORKDIR="/data"
mkdir -p ${WORKDIR}
cd ${WORKDIR}

# Download rRNA reference
if [ ! -z "${S3_REFERENCE_BUCKET}" ] && [ ! -z "${RRNA_REFERENCE}" ]; then
    echo "Downloading rRNA reference from s3://${S3_REFERENCE_BUCKET}/${RRNA_REFERENCE}"
    aws s3 cp "s3://${S3_REFERENCE_BUCKET}/${RRNA_REFERENCE}" ./rrna_reference.fa
fi

# Step 1: Download SRA data
echo "Downloading SRA data for ${SRA_ACCESSION}"
prefetch ${SRA_ACCESSION}
cd ${SRA_ACCESSION}

# Step 2: Extract FASTQ files
echo "Extracting FASTQ files"
fasterq-dump --split-files --threads ${THREADS} ${SRA_ACCESSION}

# Step 3: Compress with pigz
echo "Compressing FASTQ files"
pigz -p ${THREADS} ${SRA_ACCESSION}_1.fastq
pigz -p ${THREADS} ${SRA_ACCESSION}_2.fastq

# Check if paired-end
if [ -f "${SRA_ACCESSION}_1.fastq.gz" ] && [ -f "${SRA_ACCESSION}_2.fastq.gz" ]; then
    IS_PAIRED=true
    echo "Detected paired-end reads"
else
    IS_PAIRED=false
    echo "Detected single-end reads"
    # If not paired, rename to _1
    if [ ! -f "${SRA_ACCESSION}_1.fastq.gz" ] && [ -f "${SRA_ACCESSION}.fastq.gz" ]; then
        mv ${SRA_ACCESSION}.fastq.gz ${SRA_ACCESSION}_1.fastq.gz
    fi
fi

# Step 4: Quality control with fastp
echo "Running fastp for quality control"
if [ "$IS_PAIRED" = true ]; then
    fastp \
        -i ${SRA_ACCESSION}_1.fastq.gz \
        -I ${SRA_ACCESSION}_2.fastq.gz \
        -o ${SRA_ACCESSION}_trimmed_1.fastq.gz \
        -O ${SRA_ACCESSION}_trimmed_2.fastq.gz \
        --thread ${THREADS} \
        --html ${SRA_ACCESSION}_fastp.html \
        --json ${SRA_ACCESSION}_fastp.json
else
    fastp \
        -i ${SRA_ACCESSION}_1.fastq.gz \
        -o ${SRA_ACCESSION}_trimmed_1.fastq.gz \
        --thread ${THREADS} \
        --html ${SRA_ACCESSION}_fastp.html \
        --json ${SRA_ACCESSION}_fastp.json
fi

# Step 5: Remove rRNA with BBDuk if reference is available
if [ -f "./rrna_reference.fa" ]; then
    echo "Removing rRNA sequences with BBDuk"
    if [ "$IS_PAIRED" = true ]; then
        bbduk.sh \
            in=${SRA_ACCESSION}_trimmed_1.fastq.gz \
            in2=${SRA_ACCESSION}_trimmed_2.fastq.gz \
            out=${SRA_ACCESSION}_filtered_1.fastq.gz \
            out2=${SRA_ACCESSION}_filtered_2.fastq.gz \
            ref=./rrna_reference.fa \
            k=31 \
            hdist=1 \
            threads=${THREADS} \
            -Xmx$((THREADS * 2))g
    else
        bbduk.sh \
            in=${SRA_ACCESSION}_trimmed_1.fastq.gz \
            out=${SRA_ACCESSION}_filtered_1.fastq.gz \
            ref=./rrna_reference.fa \
            k=31 \
            hdist=1 \
            threads=${THREADS} \
            -Xmx$((THREADS * 2))g
    fi
    
    # Use the filtered files for next steps
    READ1="${SRA_ACCESSION}_filtered_1.fastq.gz"
    if [ "$IS_PAIRED" = true ]; then
        READ2="${SRA_ACCESSION}_filtered_2.fastq.gz"
    fi
else
    echo "No rRNA reference provided, skipping rRNA filtering"
    # Use the trimmed files for next steps
    READ1="${SRA_ACCESSION}_trimmed_1.fastq.gz"
    if [ "$IS_PAIRED" = true ]; then
        READ2="${SRA_ACCESSION}_trimmed_2.fastq.gz"
    fi
fi

# Upload processed files to S3
echo "Uploading processed files to S3"
aws s3 cp ${SRA_ACCESSION}_fastp.html "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/qc/${SRA_ACCESSION}_fastp.html"
aws s3 cp ${SRA_ACCESSION}_fastp.json "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/qc/${SRA_ACCESSION}_fastp.json"
aws s3 cp ${READ1} "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reads/${SRA_ACCESSION}_1.fastq.gz"

if [ "$IS_PAIRED" = true ]; then
    aws s3 cp ${READ2} "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reads/${SRA_ACCESSION}_2.fastq.gz"
fi

# Create a manifest file
echo "Creating manifest file"
cat > ${SRA_ACCESSION}_manifest.json << EOF
{
  "sra_accession": "${SRA_ACCESSION}",
  "read_type": $([ "$IS_PAIRED" = true ] && echo "\"paired\"" || echo "\"single\""),
  "read1": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reads/${SRA_ACCESSION}_1.fastq.gz",
  $([ "$IS_PAIRED" = true ] && echo "\"read2\": \"s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reads/${SRA_ACCESSION}_2.fastq.gz\",")
  "fastp_html": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/qc/${SRA_ACCESSION}_fastp.html",
  "fastp_json": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/qc/${SRA_ACCESSION}_fastp.json",
  "processing_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

# Upload manifest
aws s3 cp ${SRA_ACCESSION}_manifest.json "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/manifest/${SRA_ACCESSION}_manifest.json"

echo "RNA-Seq read processing complete for ${SRA_ACCESSION}"
echo "Output files available at s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/"