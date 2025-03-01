#!/bin/bash
set -e

# Required environment variables:
# INPUT_BUCKET - S3 bucket containing input files
# INPUT_PREFIX - S3 prefix for input files
# OUTPUT_BUCKET - S3 bucket for output
# OUTPUT_PREFIX - S3 prefix for output
# EGGNOG_DB_BUCKET - S3 bucket containing eggNOG database
# EGGNOG_DB_PATH - Path to eggNOG database within bucket
# THREADS - Number of threads to use (default: 8)

echo "Starting RNA-Seq annotation"
echo "Input bucket: ${INPUT_BUCKET}"
echo "Input prefix: ${INPUT_PREFIX}"
echo "Output bucket: ${OUTPUT_BUCKET}"
echo "Output prefix: ${OUTPUT_PREFIX}"
echo "EggNOG DB bucket: ${EGGNOG_DB_BUCKET}"
echo "EggNOG DB path: ${EGGNOG_DB_PATH}"

# Set defaults
THREADS=${THREADS:-8}
WORKDIR="/data"
mkdir -p ${WORKDIR}
cd ${WORKDIR}

# Create directories
mkdir -p assembly annotation eggnog-db

# Download assembly files
echo "Downloading assembly files from s3://${INPUT_BUCKET}/${INPUT_PREFIX}/"
aws s3 cp "s3://${INPUT_BUCKET}/${INPUT_PREFIX}/assembly/" assembly/ --recursive

# Determine sample name from assembly folder
cd assembly
SAMPLE_DIR=$(find . -type d -name "*" | head -1)
SAMPLE_NAME=$(basename ${SAMPLE_DIR})
if [ -z "${SAMPLE_NAME}" ]; then
    SAMPLE_NAME=$(ls -1 */transcripts.fasta | head -1 | cut -d/ -f1)
fi

echo "Sample name: ${SAMPLE_NAME}"
cd ${WORKDIR}

# Download eggNOG database if specified
if [ ! -z "${EGGNOG_DB_BUCKET}" ] && [ ! -z "${EGGNOG_DB_PATH}" ]; then
    echo "Downloading eggNOG database from s3://${EGGNOG_DB_BUCKET}/${EGGNOG_DB_PATH}/"
    aws s3 cp "s3://${EGGNOG_DB_BUCKET}/${EGGNOG_DB_PATH}/" eggnog-db/ --recursive
    export EGGNOG_DATA_DIR=${WORKDIR}/eggnog-db
fi

# Create annotation directory for sample
mkdir -p annotation/${SAMPLE_NAME}

# Run TransDecoder to identify coding regions
echo "Running TransDecoder on transcripts"
cd annotation/${SAMPLE_NAME}

# Extract longest ORFs
TransDecoder.LongOrfs -t ${WORKDIR}/assembly/${SAMPLE_NAME}/transcripts.fasta

# Predict likely coding regions
TransDecoder.Predict -t ${WORKDIR}/assembly/${SAMPLE_NAME}/transcripts.fasta --single_best_only

# Run eggNOG-mapper for functional annotation
echo "Running eggNOG-mapper for functional annotation"
if [ -d "${WORKDIR}/eggnog-db" ]; then
    # Run with local database
    emapper.py \
        -i transcripts.fasta.transdecoder.pep \
        --output ${SAMPLE_NAME}_eggnog \
        --cpu ${THREADS} \
        -m diamond
else
    # Run with online database (not recommended for production)
    emapper.py \
        -i transcripts.fasta.transdecoder.pep \
        --output ${SAMPLE_NAME}_eggnog \
        --cpu ${THREADS} \
        -m diamond \
        --data_dir ${EGGNOG_DATA_DIR}
fi

cd ${WORKDIR}

# Create a summary report
echo "Creating summary report"
cat > annotation_report.md << EOF
# RNA-Seq Annotation Report for ${SAMPLE_NAME}

## TransDecoder Statistics
- Number of transcripts: $(grep -c ">" assembly/${SAMPLE_NAME}/transcripts.fasta)
- Number of predicted proteins: $(grep -c ">" annotation/${SAMPLE_NAME}/transcripts.fasta.transdecoder.pep)

## eggNOG-mapper Statistics
- Number of annotated proteins: $(wc -l < annotation/${SAMPLE_NAME}/${SAMPLE_NAME}_eggnog.emapper.annotations)
- Annotation method: diamond

## Summary
- Processing date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

# Upload results to S3
echo "Uploading annotation results to S3"
aws s3 cp annotation/${SAMPLE_NAME}/transcripts.fasta.transdecoder.pep "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/annotation/${SAMPLE_NAME}/proteins.pep"
aws s3 cp annotation/${SAMPLE_NAME}/transcripts.fasta.transdecoder.gff3 "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/annotation/${SAMPLE_NAME}/proteins.gff3"
aws s3 cp annotation/${SAMPLE_NAME}/${SAMPLE_NAME}_eggnog.emapper.annotations "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/annotation/${SAMPLE_NAME}/eggnog_annotations.tsv"
aws s3 cp annotation/${SAMPLE_NAME}/${SAMPLE_NAME}_eggnog.emapper.hits "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/annotation/${SAMPLE_NAME}/eggnog_hits.tsv"
aws s3 cp annotation_report.md "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reports/${SAMPLE_NAME}_annotation_report.md"

# Create a manifest file
echo "Creating manifest file"
cat > ${SAMPLE_NAME}_manifest.json << EOF
{
  "sample_name": "${SAMPLE_NAME}",
  "proteins_file": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/annotation/${SAMPLE_NAME}/proteins.pep",
  "gff_file": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/annotation/${SAMPLE_NAME}/proteins.gff3",
  "eggnog_annotations": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/annotation/${SAMPLE_NAME}/eggnog_annotations.tsv",
  "eggnog_hits": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/annotation/${SAMPLE_NAME}/eggnog_hits.tsv",
  "report": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reports/${SAMPLE_NAME}_annotation_report.md",
  "processing_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

# Upload manifest
aws s3 cp ${SAMPLE_NAME}_manifest.json "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/manifest/${SAMPLE_NAME}_annotation_manifest.json"

echo "RNA-Seq annotation complete for ${SAMPLE_NAME}"
echo "Output files available at s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/"