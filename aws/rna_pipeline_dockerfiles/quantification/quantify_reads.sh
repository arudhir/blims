#!/bin/bash
set -e

# Required environment variables:
# INPUT_BUCKET - S3 bucket containing input files
# INPUT_PREFIX - S3 prefix for input files
# OUTPUT_BUCKET - S3 bucket for output
# OUTPUT_PREFIX - S3 prefix for output
# REFERENCE_BUCKET - S3 bucket containing reference index
# REFERENCE_INDEX - Path to salmon index within reference bucket
# THREADS - Number of threads to use (default: 8)

echo "Starting RNA-Seq quantification with Salmon"
echo "Input bucket: ${INPUT_BUCKET}"
echo "Input prefix: ${INPUT_PREFIX}"
echo "Output bucket: ${OUTPUT_BUCKET}"
echo "Output prefix: ${OUTPUT_PREFIX}"
echo "Reference bucket: ${REFERENCE_BUCKET}"
echo "Reference index: ${REFERENCE_INDEX}"

# Set defaults
THREADS=${THREADS:-8}
WORKDIR="/data"
mkdir -p ${WORKDIR}
cd ${WORKDIR}

# Create directories
mkdir -p reference reads results

# Download reference index
echo "Downloading reference index from s3://${REFERENCE_BUCKET}/${REFERENCE_INDEX}/"
aws s3 cp "s3://${REFERENCE_BUCKET}/${REFERENCE_INDEX}/" reference/ --recursive

# Download input files
echo "Downloading input files from s3://${INPUT_BUCKET}/${INPUT_PREFIX}/"
aws s3 cp "s3://${INPUT_BUCKET}/${INPUT_PREFIX}/reads/" reads/ --recursive

# Determine if paired-end
cd reads
READ_FILES=(*.fastq.gz)
if [ ${#READ_FILES[@]} -eq 0 ]; then
    echo "No FASTQ files found. Check input path."
    exit 1
fi

if [[ ${#READ_FILES[@]} -ge 2 && ${READ_FILES[0]} == *_1.fastq.gz && ${READ_FILES[1]} == *_2.fastq.gz ]]; then
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
cd ${WORKDIR}

# Run Salmon quantification
echo "Running Salmon quantification"
mkdir -p results/${SAMPLE_NAME}

if [ "$IS_PAIRED" = true ]; then
    echo "Running Salmon on paired-end data"
    salmon quant \
        -i reference \
        -l A \
        -1 reads/${READ1} \
        -2 reads/${READ2} \
        -p ${THREADS} \
        --validateMappings \
        -o results/${SAMPLE_NAME}
else
    echo "Running Salmon on single-end data"
    salmon quant \
        -i reference \
        -l A \
        -r reads/${READ1} \
        -p ${THREADS} \
        --validateMappings \
        -o results/${SAMPLE_NAME}
fi

# Create a summary report
echo "Creating summary report"
cat > quantification_report.md << EOF
# Salmon Quantification Report for ${SAMPLE_NAME}

## Parameters
- Threads: ${THREADS}
- Index: ${REFERENCE_INDEX}
- Library type: auto (A)

## Summary
- Read type: $([ "$IS_PAIRED" = true ] && echo "paired-end" || echo "single-end")
- Percent mapped: $(grep -A 1 "Mapping rate" results/${SAMPLE_NAME}/logs/salmon_quant.log | tail -n 1 | tr -d ' %')%
- Number of transcripts quantified: $(wc -l < results/${SAMPLE_NAME}/quant.sf)
- Processing date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

## Top 20 expressed transcripts
\`\`\`
$(head -n 21 results/${SAMPLE_NAME}/quant.sf)
\`\`\`
EOF

# Upload results to S3
echo "Uploading quantification results to S3"
aws s3 cp results/${SAMPLE_NAME}/ "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/quant/${SAMPLE_NAME}/" --recursive
aws s3 cp quantification_report.md "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reports/${SAMPLE_NAME}_quantification_report.md"

# Create a manifest file
echo "Creating manifest file"
cat > ${SAMPLE_NAME}_manifest.json << EOF
{
  "sample_name": "${SAMPLE_NAME}",
  "read_type": $([ "$IS_PAIRED" = true ] && echo "\"paired\"" || echo "\"single\""),
  "quant_results": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/quant/${SAMPLE_NAME}/",
  "quant_sf": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/quant/${SAMPLE_NAME}/quant.sf",
  "report": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reports/${SAMPLE_NAME}_quantification_report.md",
  "processing_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

# Upload manifest
aws s3 cp ${SAMPLE_NAME}_manifest.json "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/manifest/${SAMPLE_NAME}_quantification_manifest.json"

echo "RNA-Seq quantification complete for ${SAMPLE_NAME}"
echo "Output files available at s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/"