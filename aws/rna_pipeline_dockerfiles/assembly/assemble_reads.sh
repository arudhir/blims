#!/bin/bash
set -e

# Required environment variables:
# INPUT_BUCKET - S3 bucket containing input files
# INPUT_PREFIX - S3 prefix for input files
# OUTPUT_BUCKET - S3 bucket for output
# OUTPUT_PREFIX - S3 prefix for output
# MEMORY_LIMIT - Memory limit in GB (default: 58)
# THREADS - Number of threads to use (default: 16)

echo "Starting RNA-Seq assembly with SPAdes"
echo "Input bucket: ${INPUT_BUCKET}"
echo "Input prefix: ${INPUT_PREFIX}"
echo "Output bucket: ${OUTPUT_BUCKET}"
echo "Output prefix: ${OUTPUT_PREFIX}"

# Set defaults
THREADS=${THREADS:-16}
MEMORY_LIMIT=${MEMORY_LIMIT:-58}
WORKDIR="/data"
mkdir -p ${WORKDIR}
cd ${WORKDIR}

# Create directories
mkdir -p reads assembly

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

# Run SPAdes assembly
echo "Running rnaSPAdes assembly"
if [ "$IS_PAIRED" = true ]; then
    echo "Running rnaSPAdes on paired-end data"
    spades.py \
        --rna \
        -1 reads/${READ1} \
        -2 reads/${READ2} \
        -o assembly/${SAMPLE_NAME} \
        -t ${THREADS} \
        -m ${MEMORY_LIMIT}
else
    echo "Running rnaSPAdes on single-end data"
    spades.py \
        --rna \
        -s reads/${READ1} \
        -o assembly/${SAMPLE_NAME} \
        -t ${THREADS} \
        -m ${MEMORY_LIMIT}
fi

# Rename transcripts with seqhash
echo "Renaming transcripts with seqhash"
mkdir -p assembly/${SAMPLE_NAME}/renamed
python3 -c "
import os
import sys
from seqhash.SeqHash import SeqHash

# Create SeqHash instance
seqhasher = SeqHash()

# Open input and output files
with open('assembly/${SAMPLE_NAME}/transcripts.fasta', 'r') as infile, \
     open('assembly/${SAMPLE_NAME}/renamed/transcripts.fasta', 'w') as outfile, \
     open('assembly/${SAMPLE_NAME}/renamed/id_mapping.tsv', 'w') as mapfile:
    
    # Write header to mapping file
    mapfile.write('original_id\tseqhash_id\n')
    
    # Process each sequence
    seq_id = ''
    seq = ''
    for line in infile:
        line = line.strip()
        if line.startswith('>'):
            # Process previous sequence
            if seq:
                seqhash_id = seqhasher.hash_sequence(seq)
                outfile.write(f'>{seqhash_id} {seq_id}\n{seq}\n')
                mapfile.write(f'{seq_id}\t{seqhash_id}\n')
            
            # Start new sequence
            seq_id = line[1:]
            seq = ''
        else:
            seq += line
    
    # Process the last sequence
    if seq:
        seqhash_id = seqhasher.hash_sequence(seq)
        outfile.write(f'>{seqhash_id} {seq_id}\n{seq}\n')
        mapfile.write(f'{seq_id}\t{seqhash_id}\n')
"

# Create a summary report
echo "Creating summary report"
seqkit stats assembly/${SAMPLE_NAME}/transcripts.fasta > assembly_stats.txt
seqkit stats assembly/${SAMPLE_NAME}/renamed/transcripts.fasta >> assembly_stats.txt

cat > assembly_report.md << EOF
# RNA-Seq Assembly Report for ${SAMPLE_NAME}

## Parameters
- Assembler: rnaSPAdes
- Threads: ${THREADS}
- Memory limit: ${MEMORY_LIMIT} GB

## Assembly Statistics
\`\`\`
$(cat assembly_stats.txt)
\`\`\`

## SPAdes Log Summary
\`\`\`
$(grep "SPAdes pipeline finished" assembly/${SAMPLE_NAME}/spades.log -A 2 -B 2)
\`\`\`

## Summary
- Read type: $([ "$IS_PAIRED" = true ] && echo "paired-end" || echo "single-end")
- Number of transcripts: $(grep -c ">" assembly/${SAMPLE_NAME}/transcripts.fasta)
- N50: $(cat assembly/${SAMPLE_NAME}/transcripts.fasta | awk '/^>/ {if (seqlen) {print seqlen}; seqlen=0; next;} {seqlen+=length(\$0);} END {if (seqlen) {print seqlen;}}' | sort -n | awk '{arr[\$0]=1;} END {n=0; for (i in arr) {n++;}; print n;}')
- Processing date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
EOF

# Upload results to S3
echo "Uploading assembly results to S3"
aws s3 cp assembly/${SAMPLE_NAME}/transcripts.fasta "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/assembly/${SAMPLE_NAME}/transcripts.fasta"
aws s3 cp assembly/${SAMPLE_NAME}/renamed/transcripts.fasta "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/assembly/${SAMPLE_NAME}/renamed_transcripts.fasta"
aws s3 cp assembly/${SAMPLE_NAME}/renamed/id_mapping.tsv "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/assembly/${SAMPLE_NAME}/id_mapping.tsv"
aws s3 cp assembly/${SAMPLE_NAME}/spades.log "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/assembly/${SAMPLE_NAME}/spades.log"
aws s3 cp assembly_report.md "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reports/${SAMPLE_NAME}_assembly_report.md"

# Create a manifest file
echo "Creating manifest file"
cat > ${SAMPLE_NAME}_manifest.json << EOF
{
  "sample_name": "${SAMPLE_NAME}",
  "read_type": $([ "$IS_PAIRED" = true ] && echo "\"paired\"" || echo "\"single\""),
  "transcripts_fasta": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/assembly/${SAMPLE_NAME}/transcripts.fasta",
  "renamed_transcripts_fasta": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/assembly/${SAMPLE_NAME}/renamed_transcripts.fasta",
  "id_mapping": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/assembly/${SAMPLE_NAME}/id_mapping.tsv",
  "spades_log": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/assembly/${SAMPLE_NAME}/spades.log",
  "report": "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/reports/${SAMPLE_NAME}_assembly_report.md",
  "processing_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

# Upload manifest
aws s3 cp ${SAMPLE_NAME}_manifest.json "s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/manifest/${SAMPLE_NAME}_assembly_manifest.json"

echo "RNA-Seq assembly complete for ${SAMPLE_NAME}"
echo "Output files available at s3://${OUTPUT_BUCKET}/${OUTPUT_PREFIX}/"