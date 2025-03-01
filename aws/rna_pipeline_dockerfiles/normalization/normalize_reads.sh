#!/bin/bash
set -e

# Required environment variables:
# INPUT_BUCKET - S3 bucket containing input files
# INPUT_PREFIX - S3 prefix for input files
# OUTPUT_BUCKET - S3 bucket for output
# OUTPUT_PREFIX - S3 prefix for output
# TARGET_DEPTH - Target depth for normalization (default: 100)
# MIN_DEPTH - Minimum depth for normalization (default: 5)
# THREADS - Number of threads to use (default: 8)

echo "Starting RNA-Seq read normalization"
echo "Input bucket: ${INPUT_BUCKET}"
echo "Input prefix: ${INPUT_PREFIX}"
echo "Output bucket: ${OUTPUT_BUCKET}"
echo "Output prefix: ${OUTPUT_PREFIX}"

# Set defaults
THREADS=${THREADS:-8}
TARGET_DEPTH=${TARGET_DEPTH:-100}
MIN_DEPTH=${MIN_DEPTH:-5}
WORKDIR="/data"
mkdir -p ${WORKDIR}
cd ${WORKDIR}

# Download input files
echo "Downloading input files from s3://${INPUT_BUCKET}/${INPUT_PREFIX}/"
aws s3 cp "s3://${INPUT_BUCKET}/${INPUT_PREFIX}/reads/" . --recursive

# Determine if paired-end
READ_FILES=(*.fastq.gz)
if [ ${#READ_FILES[@]} -eq 0 ]; then
    echo "No FASTQ files found. Check input path."
    exit 1
fi

if [[ ${#READ_FILES[@]} -eq 2 || ${#READ_FILES[@]} -gt 2 && ${READ_FILES[0]} == *_1.fastq.gz && ${READ_FILES[1]} == *_2.fastq.gz ]]; then
    IS_PAIRED=true
    echo "Detected paired-end reads"
    READ1=${READ_FILES[0]}
    READ2=${READ_FILES[1]}
    SAMPLE_NAME=$(basename ${READ1} _1.fastq.gz)
else
    IS_PAIRED=false
    echo "Detected single-end reads"
    READ1=${READ_FILES[0]}
    SAMPLE_NAME=$(basename ${READ1} _1.fastq.gz)
    if [ "$SAMPLE_NAME" == "${READ1}" ]; then
        SAMPLE_NAME=$(basename ${READ1} .fastq.gz)
    fi
fi

echo "Sample name: ${SAMPLE_NAME}"

# Create output directory
mkdir -p normalized

# Run bbnorm for normalization
if [ "$IS_PAIRED" = true ]; then
    echo "Running normalization on paired-end data"
    bbnorm.sh \
        in=${READ1} \
        in2=${READ2} \
        out=normalized/${SAMPLE_NAME}_normalized_1.fastq.gz \
        out2=normalized/${SAMPLE_NAME}_normalized_2.fastq.gz \
        target=${TARGET_DEPTH} \
        min=${MIN_DEPTH} \
        threads=${THREADS} \
        -Xmx$((THREADS * 2))g
else
    echo "Running normalization on single-end data"
    bbnorm.sh \
        in=${READ1} \
        out=normalized/${SAMPLE_NAME}_normalized_1.fastq.gz \
        target=${TARGET_DEPTH} \
        min=${MIN_DEPTH} \
        threads=${THREADS} \
        -Xmx$((THREADS * 2))g
fi

# Create a summary report
echo "Creating summary report"
seqkit stats ${READ1} > original_stats.txt
if [ "$IS_PAIRED" = true ]; then
    seqkit stats ${READ2} >> original_stats.txt
fi
seqkit stats normalized/${SAMPLE_NAME}_normalized_1.fastq.gz > normalized_stats.txt
if [ "$IS_PAIRED" = true ]; then
    seqkit stats normalized/${SAMPLE_NAME}_normalized_2.fastq.gz >> normalized_stats.txt
fi

cat > normalization_report.md << EOF
# Normalization Report for ${SAMPLE_NAME}

## Parameters
- Target depth: ${TARGET_DEPTH}
- Minimum depth: ${MIN_DEPTH}
- Threads: ${THREADS}

## Original Stats
\`\`\`
$(cat original_stats.txt)
\`\`\`

## Normalized Stats
\`\`\`
$(cat normalized_stats.txt)
\`\`\`

## Summary
- Read type: $([ "$IS_PAIRED" = true ] && echo "paired-end" || echo "single-end")
- Processing date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

# Upload processed files to S3
echo "Uploading normalized files to S3"
aws s3 cp normalized/${SAMPLE_NAME}_normalized_1.fastq.gz "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reads/${SAMPLE_NAME}_normalized_1.fastq.gz"
if [ "$IS_PAIRED" = true ]; then
    aws s3 cp normalized/${SAMPLE_NAME}_normalized_2.fastq.gz "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reads/${SAMPLE_NAME}_normalized_2.fastq.gz"
fi
aws s3 cp normalization_report.md "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reports/${SAMPLE_NAME}_normalization_report.md"

# Create a manifest file
echo "Creating manifest file"
cat > ${SAMPLE_NAME}_manifest.json << EOF
{
  "sample_name": "${SAMPLE_NAME}",
  "read_type": $([ "$IS_PAIRED" = true ] && echo "\"paired\"" || echo "\"single\""),
  "normalized_read1": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reads/${SAMPLE_NAME}_normalized_1.fastq.gz",
  $([ "$IS_PAIRED" = true ] && echo "\"normalized_read2\": \"s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reads/${SAMPLE_NAME}_normalized_2.fastq.gz\",")
  "report": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reports/${SAMPLE_NAME}_normalization_report.md",
  "normalization_params": {
    "target_depth": ${TARGET_DEPTH},
    "min_depth": ${MIN_DEPTH}
  },
  "processing_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

# Upload manifest
aws s3 cp ${SAMPLE_NAME}_manifest.json "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/manifest/${SAMPLE_NAME}_normalization_manifest.json"

echo "RNA-Seq read normalization complete for ${SAMPLE_NAME}"
echo "Output files available at s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/"