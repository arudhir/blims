#!/bin/bash
set -e

# Required environment variables:
# SAMPLE_ID - Sample ID for metadata
# INPUT_BUCKET - S3 bucket containing input files
# INPUT_PREFIX - S3 prefix for input files
# OUTPUT_BUCKET - S3 bucket for output
# DB_BUCKET - S3 bucket containing the master database
# DB_PATH - Path to master database within bucket
# THREADS - Number of threads to use (default: 4)

echo "Starting RNA-Seq database update"
echo "Sample ID: ${SAMPLE_ID}"
echo "Input bucket: ${INPUT_BUCKET}"
echo "Input prefix: ${INPUT_PREFIX}"
echo "Output bucket: ${OUTPUT_BUCKET}"
echo "DB bucket: ${DB_BUCKET}"
echo "DB path: ${DB_PATH}"

# Set defaults
THREADS=${THREADS:-4}
WORKDIR="/data"
mkdir -p ${WORKDIR}
cd ${WORKDIR}

# Create directories
mkdir -p quant annotation db

# Download quantification results
echo "Downloading quantification results from s3://${INPUT_BUCKET}/${INPUT_PREFIX}/quant/"
aws s3 cp "s3://${INPUT_BUCKET}/${INPUT_PREFIX}/quant/" quant/ --recursive

# Download annotation results
echo "Downloading annotation results from s3://${INPUT_BUCKET}/${INPUT_PREFIX}/annotation/"
aws s3 cp "s3://${INPUT_BUCKET}/${INPUT_PREFIX}/annotation/" annotation/ --recursive

# Download master database if it exists
if [ ! -z "${DB_BUCKET}" ] && [ ! -z "${DB_PATH}" ]; then
    echo "Downloading master database from s3://${DB_BUCKET}/${DB_PATH}/"
    aws s3 cp "s3://${DB_BUCKET}/${DB_PATH}/rna_master.duckdb" db/ || echo "No master database found. Will create a new one."
fi

# Run database update Python script
echo "Running database update script"
python3 /usr/local/bin/update_database.py \
    --sample-id ${SAMPLE_ID} \
    --quant-dir ${WORKDIR}/quant \
    --annot-dir ${WORKDIR}/annotation \
    --db-dir ${WORKDIR}/db \
    --threads ${THREADS}

# Upload sample database to S3
echo "Uploading sample database to S3"
aws s3 cp ${WORKDIR}/db/${SAMPLE_ID}.duckdb "s3://${OUTPUT_BUCKET}/${INPUT_PREFIX}/db/${SAMPLE_ID}.duckdb"

# Upload/update master database if needed
if [ -f "${WORKDIR}/db/rna_master.duckdb" ]; then
    echo "Uploading master database to S3"
    aws s3 cp ${WORKDIR}/db/rna_master.duckdb "s3://${DB_BUCKET}/${DB_PATH}/rna_master.duckdb"
fi

# Create a summary report
echo "Creating summary report"
cat > database_update_report.md << EOF
# RNA-Seq Database Update Report for ${SAMPLE_ID}

## Database Information
- Sample database: ${SAMPLE_ID}.duckdb
- Master database: rna_master.duckdb

## Tables
- transcripts: Information about assembled transcripts
- proteins: Information about predicted proteins
- annotations: Functional annotations from eggNOG-mapper
- expression: Expression levels from Salmon

## Summary
- Processing date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

# Upload report
aws s3 cp database_update_report.md "s3://${OUTPUT_BUCKET}/${INPUT_PREFIX}/reports/${SAMPLE_ID}_database_update_report.md"

# Create a manifest file
echo "Creating manifest file"
cat > ${SAMPLE_ID}_manifest.json << EOF
{
  "sample_id": "${SAMPLE_ID}",
  "sample_database": "s3://${OUTPUT_BUCKET}/${INPUT_PREFIX}/db/${SAMPLE_ID}.duckdb",
  "master_database": "s3://${DB_BUCKET}/${DB_PATH}/rna_master.duckdb",
  "report": "s3://${OUTPUT_BUCKET}/${INPUT_PREFIX}/reports/${SAMPLE_ID}_database_update_report.md",
  "processing_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

# Upload manifest
aws s3 cp ${SAMPLE_ID}_manifest.json "s3://${OUTPUT_BUCKET}/${INPUT_PREFIX}/manifest/${SAMPLE_ID}_database_manifest.json"

echo "RNA-Seq database update complete for ${SAMPLE_ID}"
echo "Output files available at s3://${OUTPUT_BUCKET}/${INPUT_PREFIX}/"