#!/usr/bin/env python3
"""
Database update script for RNA-Seq pipeline.
This script processes quantification and annotation results and stores them in a DuckDB database.
"""

import argparse
import os
import sys
import glob
import pandas as pd
import duckdb
import json
from pathlib import Path


def setup_database(db_path, sample_id):
    """Setup sample database and create necessary tables"""
    # Connect to database
    con = duckdb.connect(db_path)
    
    # Create transcripts table
    con.execute("""
    CREATE TABLE IF NOT EXISTS transcripts (
        transcript_id VARCHAR PRIMARY KEY,
        sample_id VARCHAR,
        length INTEGER,
        gc_content DOUBLE,
        original_id VARCHAR
    )
    """)
    
    # Create proteins table
    con.execute("""
    CREATE TABLE IF NOT EXISTS proteins (
        protein_id VARCHAR PRIMARY KEY,
        transcript_id VARCHAR,
        sample_id VARCHAR,
        length INTEGER,
        original_id VARCHAR,
        FOREIGN KEY (transcript_id) REFERENCES transcripts(transcript_id)
    )
    """)
    
    # Create annotations table
    con.execute("""
    CREATE TABLE IF NOT EXISTS annotations (
        annotation_id INTEGER PRIMARY KEY,
        protein_id VARCHAR,
        eggnog_id VARCHAR,
        go_terms VARCHAR,
        kegg_id VARCHAR,
        kegg_pathway VARCHAR,
        gene_name VARCHAR,
        description VARCHAR,
        sample_id VARCHAR,
        FOREIGN KEY (protein_id) REFERENCES proteins(protein_id)
    )
    """)
    
    # Create expression table
    con.execute("""
    CREATE TABLE IF NOT EXISTS expression (
        transcript_id VARCHAR,
        sample_id VARCHAR,
        tpm DOUBLE,
        num_reads DOUBLE,
        eff_length DOUBLE,
        PRIMARY KEY (transcript_id, sample_id),
        FOREIGN KEY (transcript_id) REFERENCES transcripts(transcript_id)
    )
    """)
    
    # Create samples table
    con.execute("""
    CREATE TABLE IF NOT EXISTS samples (
        sample_id VARCHAR PRIMARY KEY,
        sra_accession VARCHAR,
        metadata VARCHAR,
        processing_date VARCHAR
    )
    """)
    
    # Insert sample record if not exists
    con.execute("""
    INSERT OR IGNORE INTO samples (sample_id, processing_date)
    VALUES (?, CURRENT_TIMESTAMP)
    """, [sample_id])
    
    con.close()
    
    return db_path


def process_quantification(quant_dir, db_path, sample_id):
    """Process salmon quantification results"""
    print(f"Processing quantification data in {quant_dir}")
    
    # Look for quant.sf files
    quant_files = glob.glob(os.path.join(quant_dir, "**", "quant.sf"), recursive=True)
    
    if not quant_files:
        print("No quantification files found.")
        return
    
    # Use the first file found
    quant_file = quant_files[0]
    print(f"Using quantification file: {quant_file}")
    
    # Read the quantification file
    quant_df = pd.read_csv(quant_file, sep='\t')
    
    # Connect to the database
    con = duckdb.connect(db_path)
    
    # Insert expression data
    for _, row in quant_df.iterrows():
        transcript_id = row['Name']
        tpm = row['TPM']
        eff_length = row['EffectiveLength']
        num_reads = row['NumReads']
        
        con.execute("""
        INSERT OR REPLACE INTO expression (transcript_id, sample_id, tpm, num_reads, eff_length)
        VALUES (?, ?, ?, ?, ?)
        """, [transcript_id, sample_id, tpm, num_reads, eff_length])
    
    con.close()
    print(f"Processed {len(quant_df)} transcript expression records")


def process_annotation(annot_dir, db_path, sample_id):
    """Process TransDecoder and eggNOG-mapper annotation results"""
    print(f"Processing annotation data in {annot_dir}")
    
    # Look for protein files
    protein_files = glob.glob(os.path.join(annot_dir, "**", "proteins.pep"), recursive=True)
    
    if not protein_files:
        print("No protein files found.")
        return
    
    # Use the first file found
    protein_file = protein_files[0]
    print(f"Using protein file: {protein_file}")
    
    # Look for annotation files
    annot_files = glob.glob(os.path.join(annot_dir, "**", "eggnog_annotations.tsv"), recursive=True)
    
    if not annot_files:
        print("No annotation files found.")
        return
    
    # Use the first file found
    annot_file = annot_files[0]
    print(f"Using annotation file: {annot_file}")
    
    # Parse protein file to get transcript to protein mapping
    transcript_protein_map = {}
    current_protein = ""
    with open(protein_file, 'r') as f:
        for line in f:
            if line.startswith('>'):
                # Extract protein ID and transcript ID from header
                # Format: >GENE.1.pep transcript=GENE.1
                header = line.strip()[1:]
                parts = header.split(' ')
                protein_id = parts[0]
                transcript_id = None
                
                for part in parts:
                    if part.startswith('transcript='):
                        transcript_id = part.split('=')[1]
                        break
                
                if transcript_id:
                    transcript_protein_map[protein_id] = transcript_id
                    current_protein = protein_id
    
    # Parse annotation file
    if os.path.exists(annot_file):
        annot_df = pd.read_csv(annot_file, sep='\t', comment='#')
        
        # Connect to the database
        con = duckdb.connect(db_path)
        
        # Insert protein and annotation data
        for _, row in annot_df.iterrows():
            try:
                protein_id = row['#query']
                transcript_id = transcript_protein_map.get(protein_id, "unknown")
                
                # Get GO terms
                go_terms = row.get('GOs', '')
                
                # Get KEGG info
                kegg_id = row.get('KEGG_ko', '')
                kegg_pathway = row.get('KEGG_Pathway', '')
                
                # Get description
                gene_name = row.get('Preferred_name', '')
                description = row.get('Description', '')
                
                # Store protein in database
                con.execute("""
                INSERT OR IGNORE INTO proteins 
                (protein_id, transcript_id, sample_id, original_id)
                VALUES (?, ?, ?, ?)
                """, [protein_id, transcript_id, sample_id, protein_id])
                
                # Store annotation in database
                con.execute("""
                INSERT INTO annotations 
                (protein_id, eggnog_id, go_terms, kegg_id, kegg_pathway, 
                gene_name, description, sample_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, [protein_id, row.get('eggNOG_OGs', ''), go_terms, kegg_id, 
                     kegg_pathway, gene_name, description, sample_id])
                
            except Exception as e:
                print(f"Error processing annotation row: {e}")
        
        con.close()
        print(f"Processed {len(annot_df)} annotation records")


def update_master_database(sample_db_path, master_db_path):
    """Update master database with sample database data"""
    print(f"Updating master database: {master_db_path}")
    
    # Create master database if it doesn't exist
    if not os.path.exists(master_db_path):
        print("Creating new master database")
        setup_database(master_db_path, "master")
    
    # Connect to both databases
    sample_con = duckdb.connect(sample_db_path)
    master_con = duckdb.connect(master_db_path)
    
    # Copy data from sample database to master database
    
    # Transcripts
    transcript_df = sample_con.execute("SELECT * FROM transcripts").fetchdf()
    for _, row in transcript_df.iterrows():
        master_con.execute("""
        INSERT OR IGNORE INTO transcripts 
        (transcript_id, sample_id, length, gc_content, original_id)
        VALUES (?, ?, ?, ?, ?)
        """, [row['transcript_id'], row['sample_id'], row['length'], 
             row['gc_content'], row['original_id']])
    
    # Proteins
    protein_df = sample_con.execute("SELECT * FROM proteins").fetchdf()
    for _, row in protein_df.iterrows():
        master_con.execute("""
        INSERT OR IGNORE INTO proteins 
        (protein_id, transcript_id, sample_id, length, original_id)
        VALUES (?, ?, ?, ?, ?)
        """, [row['protein_id'], row['transcript_id'], row['sample_id'], 
             row['length'], row['original_id']])
    
    # Annotations
    annot_df = sample_con.execute("SELECT * FROM annotations").fetchdf()
    for _, row in annot_df.iterrows():
        master_con.execute("""
        INSERT INTO annotations 
        (protein_id, eggnog_id, go_terms, kegg_id, kegg_pathway, 
        gene_name, description, sample_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [row['protein_id'], row['eggnog_id'], row['go_terms'], 
             row['kegg_id'], row['kegg_pathway'], row['gene_name'], 
             row['description'], row['sample_id']])
    
    # Expression
    expr_df = sample_con.execute("SELECT * FROM expression").fetchdf()
    for _, row in expr_df.iterrows():
        master_con.execute("""
        INSERT OR REPLACE INTO expression 
        (transcript_id, sample_id, tpm, num_reads, eff_length)
        VALUES (?, ?, ?, ?, ?)
        """, [row['transcript_id'], row['sample_id'], row['tpm'], 
             row['num_reads'], row['eff_length']])
    
    # Samples
    sample_df = sample_con.execute("SELECT * FROM samples").fetchdf()
    for _, row in sample_df.iterrows():
        master_con.execute("""
        INSERT OR REPLACE INTO samples 
        (sample_id, sra_accession, metadata, processing_date)
        VALUES (?, ?, ?, ?)
        """, [row['sample_id'], row['sra_accession'], row['metadata'], 
             row['processing_date']])
    
    sample_con.close()
    master_con.close()
    
    print("Master database update complete")


def main():
    parser = argparse.ArgumentParser(description="Update DuckDB database with RNA-Seq pipeline results")
    parser.add_argument("--sample-id", required=True, help="Sample ID for database records")
    parser.add_argument("--quant-dir", required=True, help="Directory containing quantification results")
    parser.add_argument("--annot-dir", required=True, help="Directory containing annotation results")
    parser.add_argument("--db-dir", required=True, help="Directory for database files")
    parser.add_argument("--threads", type=int, default=4, help="Number of threads to use")
    
    args = parser.parse_args()
    
    # Create database directory if it doesn't exist
    os.makedirs(args.db_dir, exist_ok=True)
    
    # Setup sample database
    sample_db_path = os.path.join(args.db_dir, f"{args.sample_id}.duckdb")
    setup_database(sample_db_path, args.sample_id)
    
    # Process quantification results
    process_quantification(args.quant_dir, sample_db_path, args.sample_id)
    
    # Process annotation results
    process_annotation(args.annot_dir, sample_db_path, args.sample_id)
    
    # Update master database if it exists
    master_db_path = os.path.join(args.db_dir, "rna_master.duckdb")
    if os.path.exists(master_db_path) or os.path.exists(os.path.dirname(master_db_path)):
        update_master_database(sample_db_path, master_db_path)
    
    print(f"Database update complete for sample {args.sample_id}")


if __name__ == "__main__":
    main()