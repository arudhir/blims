"""BLIMS Streamlit application."""

import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import uuid
from datetime import datetime, timedelta
import time
from typing import Dict, Any, List

# Import BLIMS modules
from blims.models.sample import Sample
from blims.models.job import Job, JobStatus, JobType
from blims.repositories.sample_repository import SampleRepository
from blims.repositories.job_repository import JobRepository
from blims.services.sample_service import SampleService
from blims.services.job_service import JobService
from blims.core.container_manager import ContainerManager
from blims.utils.visualization import (
    create_sample_network, 
    draw_network_matplotlib,
    draw_network_pyvis
)

# Initialize services
sample_repository = SampleRepository()
job_repository = JobRepository()
sample_service = SampleService(sample_repository)
job_service = JobService(job_repository, sample_service)
container_manager = ContainerManager(sample_service)

# Set page configuration
st.set_page_config(
    page_title="BLIMS - Bioinformatics Laboratory Information Management System",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Title and description
st.title("BLIMS: Bioinformatics Laboratory Information Management System")
st.markdown("""
This is a web-based interface to the BLIMS system for managing samples, 
containers, and bioinformatics data.
""")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select a page:",
    ["Sample Management", "Container Management", "Sample Network", "Bioinformatics Pipeline", "Job Dashboard", "Batch Processing"]
)

# Function to display a sample form
def sample_form(existing_sample=None):
    with st.form("sample_form"):
        if existing_sample:
            st.subheader(f"Edit Sample: {existing_sample.name}")
            sample_id = existing_sample.id
            default_name = existing_sample.name
            default_type = existing_sample.sample_type
            default_barcode = existing_sample.barcode or ""
            default_container = str(existing_sample.container_id) if existing_sample.container_id else ""
            default_metadata = existing_sample.metadata
        else:
            st.subheader("Create New Sample")
            sample_id = None
            default_name = ""
            default_type = ""
            default_barcode = ""
            default_container = ""
            default_metadata = {}
        
        name = st.text_input("Sample Name", value=default_name)
        sample_type = st.text_input("Sample Type", value=default_type)
        barcode = st.text_input("Barcode (optional)", value=default_barcode)
        
        # Container selection
        containers = sample_service.get_containers()
        container_options = ["None"] + [f"{c.name} ({c.sample_id})" for c in containers]
        default_idx = 0
        
        if default_container:
            for i, opt in enumerate(container_options):
                if default_container in opt:
                    default_idx = i
                    break
                    
        container = st.selectbox(
            "Container (optional)", 
            options=container_options,
            index=default_idx
        )
        
        # Parent sample selection
        parent_samples = sample_service.get_all_samples()
        if existing_sample:
            parent_samples = [s for s in parent_samples if s.id != existing_sample.id]
            
        parent_options = ["None"] + [f"{s.name} ({s.sample_id})" for s in parent_samples]
        parent = st.selectbox("Parent Sample (optional)", options=parent_options)
        
        # Basic metadata fields
        st.subheader("Metadata")
        col1, col2 = st.columns(2)
        with col1:
            concentration = st.text_input(
                "Concentration", 
                value=default_metadata.get("concentration", "")
            )
            volume = st.text_input(
                "Volume", 
                value=default_metadata.get("volume", "")
            )
        
        with col2:
            date_collected = st.date_input(
                "Date Collected",
                value=None
            )
            location = st.text_input(
                "Storage Location", 
                value=default_metadata.get("storage_location", "")
            )
            
        # Read files
        st.subheader("Read Files")
        read_files_text = st.text_area(
            "Read File Paths (one per line)",
            value="\n".join(existing_sample.file_paths) if existing_sample else "",
            help="Enter file paths (local or S3) for read files, one per line"
        )
        
        # Form submission
        submit_button = st.form_submit_button("Save Sample")
        
        if submit_button and name and sample_type:
            # Process form data
            metadata = {}
            if concentration:
                metadata["concentration"] = concentration
            if volume:
                metadata["volume"] = volume
            if date_collected:
                metadata["date_collected"] = date_collected.isoformat()
            if location:
                metadata["storage_location"] = location
            
            # Create or update sample
            try:
                if existing_sample:
                    # Update existing sample
                    existing_sample.name = name
                    existing_sample.sample_type = sample_type
                    existing_sample.barcode = barcode if barcode else None
                    existing_sample.metadata = metadata
                    
                    # Process read files
                    if read_files_text.strip():
                        # Clear existing files and add new ones
                        existing_sample.file_paths = []
                        for file_path in read_files_text.strip().split("\n"):
                            file_path = file_path.strip()
                            if file_path:
                                existing_sample.add_file(file_path)
                    
                    # Handle container change
                    if container != "None":
                        container_id = container.split("(")[1].split(")")[0]
                        container_sample = sample_service.get_sample_by_sample_id(container_id)
                        if container_sample:
                            container_manager.add_sample_to_container(existing_sample.id, container_sample.id)
                    else:
                        if existing_sample.container_id:
                            container_manager.remove_sample_from_container(existing_sample.id)
                    
                    # Handle parent relationship
                    if parent != "None":
                        parent_id = parent.split("(")[1].split(")")[0]
                        parent_sample = sample_service.get_sample_by_sample_id(parent_id)
                        if parent_sample:
                            existing_sample.add_parent(parent_sample.id)
                            parent_sample.add_child(existing_sample.id)
                            sample_service.update_sample(parent_sample)
                    
                    sample_service.update_sample(existing_sample)
                    st.success(f"Sample '{name}' updated successfully!")
                    return True
                else:
                    # Create new sample
                    created_by = "admin"  # In a real app, this would be the logged-in user
                    
                    new_sample = Sample(
                        name=name,
                        sample_type=sample_type,
                        created_by=created_by,
                        metadata=metadata,
                        barcode=barcode if barcode else None
                    )
                    
                    sample_service.create_sample(new_sample)
                    
                    # Process read files
                    if read_files_text.strip():
                        for file_path in read_files_text.strip().split("\n"):
                            file_path = file_path.strip()
                            if file_path:
                                new_sample.add_file(file_path)
                        sample_service.update_sample(new_sample)
                    
                    # Handle container
                    if container != "None":
                        container_id = container.split("(")[1].split(")")[0]
                        container_sample = sample_service.get_sample_by_sample_id(container_id)
                        if container_sample:
                            container_manager.add_sample_to_container(new_sample.id, container_sample.id)
                    
                    # Handle parent relationship
                    if parent != "None":
                        parent_id = parent.split("(")[1].split(")")[0]
                        parent_sample = sample_service.get_sample_by_sample_id(parent_id)
                        if parent_sample:
                            new_sample.add_parent(parent_sample.id)
                            parent_sample.add_child(new_sample.id)
                            sample_service.update_sample(parent_sample)
                            sample_service.update_sample(new_sample)
                    
                    st.success(f"Sample '{name}' created successfully!")
                    return True
            except Exception as e:
                st.error(f"Error: {str(e)}")
                return False
                
        return False

# Function to display container form
def container_form(existing_container=None):
    with st.form("container_form"):
        if existing_container:
            st.subheader(f"Edit Container: {existing_container.name}")
            default_name = existing_container.name
            default_type = existing_container.metadata.get("container_type", "")
            default_rows = existing_container.metadata.get("rows", "")
            default_columns = existing_container.metadata.get("columns", "")
            default_barcode = existing_container.barcode or ""
        else:
            st.subheader("Create New Container")
            default_name = ""
            default_type = ""
            default_rows = ""
            default_columns = ""
            default_barcode = ""
        
        name = st.text_input("Container Name", value=default_name)
        container_type = st.selectbox(
            "Container Type", 
            options=["Plate", "Rack", "Box", "Freezer", "Other"],
            index=0 if not default_type else ["Plate", "Rack", "Box", "Freezer", "Other"].index(default_type)
        )
        
        col1, col2 = st.columns(2)
        with col1:
            rows = st.text_input("Rows (optional)", value=default_rows)
        with col2:
            columns = st.text_input("Columns (optional)", value=default_columns)
            
        barcode = st.text_input("Barcode (optional)", value=default_barcode)
        
        # Parent container selection
        if existing_container:
            containers = [c for c in sample_service.get_containers() if c.id != existing_container.id]
        else:
            containers = sample_service.get_containers()
            
        parent_options = ["None"] + [f"{c.name} ({c.sample_id})" for c in containers]
        
        default_idx = 0
        if existing_container and existing_container.container_id:
            for i, opt in enumerate(parent_options):
                if str(existing_container.container_id) in opt:
                    default_idx = i
                    break
                    
        parent_container = st.selectbox(
            "Parent Container (optional)", 
            options=parent_options,
            index=default_idx
        )
        
        # Form submission
        submit_button = st.form_submit_button("Save Container")
        
        if submit_button and name and container_type:
            # Process form data
            metadata = {
                "container_type": container_type
            }
            
            if rows:
                metadata["rows"] = rows
            if columns:
                metadata["columns"] = columns
            
            try:
                created_by = "admin"  # In a real app, this would be the logged-in user
                
                if existing_container:
                    # Update existing container
                    existing_container.name = name
                    existing_container.barcode = barcode if barcode else None
                    existing_container.metadata = metadata
                    
                    # Handle parent container change
                    old_container_id = existing_container.container_id
                    new_container_id = None
                    
                    if parent_container != "None":
                        parent_id = parent_container.split("(")[1].split(")")[0]
                        parent = sample_service.get_sample_by_sample_id(parent_id)
                        if parent:
                            new_container_id = parent.id
                    
                    if old_container_id != new_container_id:
                        if old_container_id:
                            container_manager.remove_sample_from_container(existing_container.id)
                        
                        if new_container_id:
                            container_manager.add_sample_to_container(existing_container.id, new_container_id)
                    
                    sample_service.update_sample(existing_container)
                    st.success(f"Container '{name}' updated successfully!")
                    return True
                else:
                    # Create new container
                    new_container = Sample(
                        name=name,
                        sample_type="container",
                        created_by=created_by,
                        metadata=metadata,
                        barcode=barcode if barcode else None,
                        is_container=True
                    )
                    
                    sample_service.create_sample(new_container)
                    
                    # Handle parent container
                    if parent_container != "None":
                        parent_id = parent_container.split("(")[1].split(")")[0]
                        parent = sample_service.get_sample_by_sample_id(parent_id)
                        if parent:
                            container_manager.add_sample_to_container(new_container.id, parent.id)
                    
                    st.success(f"Container '{name}' created successfully!")
                    return True
            except Exception as e:
                st.error(f"Error: {str(e)}")
                return False
                
        return False

# Function to detect read files in a sample
def detect_read_files(sample):
    """Detect FASTQ read files associated with a sample.
    
    Args:
        sample: Sample object
        
    Returns:
        Dictionary containing detected read files by type
    """
    if not sample or not sample.file_paths:
        return {}
    
    reads = {
        "single_end": [],
        "paired_end_1": [],
        "paired_end_2": [],
    }
    
    # Regular expressions for common read file patterns
    import re
    single_end_patterns = [
        r'.*\.fastq$', r'.*\.fq$', r'.*\.fastq\.gz$', r'.*\.fq\.gz$'
    ]
    paired_end_r1_patterns = [
        r'.*_R1.*\.fastq$', r'.*_R1.*\.fq$', r'.*_R1.*\.fastq\.gz$', r'.*_R1.*\.fq\.gz$',
        r'.*_1\.fastq$', r'.*_1\.fq$', r'.*_1\.fastq\.gz$', r'.*_1\.fq\.gz$'
    ]
    paired_end_r2_patterns = [
        r'.*_R2.*\.fastq$', r'.*_R2.*\.fq$', r'.*_R2.*\.fastq\.gz$', r'.*_R2.*\.fq\.gz$',
        r'.*_2\.fastq$', r'.*_2\.fq$', r'.*_2\.fastq\.gz$', r'.*_2\.fq\.gz$',
    ]
    
    for file_path in sample.file_paths:
        # Check for paired-end reads first (more specific patterns)
        is_r1 = any(re.match(pattern, file_path) for pattern in paired_end_r1_patterns)
        is_r2 = any(re.match(pattern, file_path) for pattern in paired_end_r2_patterns)
        
        if is_r1:
            reads["paired_end_1"].append(file_path)
        elif is_r2:
            reads["paired_end_2"].append(file_path)
        # Only consider it single-end if it's not part of a pair
        elif any(re.match(pattern, file_path) for pattern in single_end_patterns):
            reads["single_end"].append(file_path)
    
    # Sort file lists
    reads["single_end"].sort()
    reads["paired_end_1"].sort()
    reads["paired_end_2"].sort()
    
    return reads

# Function to create a sample RNA-Seq job form
def rna_seq_form():
    st.subheader("Create RNA-Seq Analysis Pipeline")
    
    with st.form("rna_seq_form"):
        # Sample selection
        samples = [s for s in sample_service.get_all_samples() if not s.is_container]
        sample_options = [f"{s.name} ({s.sample_id})" for s in samples]
        
        if not sample_options:
            st.warning("No samples available. Please create a sample first.")
            st.form_submit_button("Submit", disabled=True)
            return False
            
        sample_selection = st.selectbox("Select Sample", options=sample_options)
        
        # SRA accession
        sra_accession = st.text_input("SRA Accession", help="e.g., SRR12345678")
        
        # Advanced parameters (collapsible)
        with st.expander("Advanced Parameters", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                rrna_reference = st.text_input(
                    "rRNA Reference Path", 
                    value="references/rrna/rrna_reference.fa",
                    help="Path to rRNA reference within S3 bucket"
                )
                target_depth = st.number_input(
                    "Normalization Target Depth", 
                    min_value=1, 
                    value=100,
                    help="Target depth for read normalization"
                )
            
            with col2:
                min_depth = st.number_input(
                    "Normalization Min Depth", 
                    min_value=1, 
                    value=5,
                    help="Minimum depth for read normalization"
                )
                reference_index = st.text_input(
                    "Reference Index Path", 
                    value="references/transcriptome/index",
                    help="Path to reference index within S3 bucket"
                )
        
        submit_button = st.form_submit_button("Create Pipeline")
        
        if submit_button and sample_selection and sra_accession:
            try:
                # Get selected sample
                sample_id = sample_selection.split("(")[1].split(")")[0]
                sample = sample_service.get_sample_by_sample_id(sample_id)
                
                if not sample:
                    st.error("Selected sample not found.")
                    return False
                
                # Create parameters dictionary
                parameters = {
                    "rrna_reference": rrna_reference,
                    "target_depth": str(target_depth),
                    "min_depth": str(min_depth),
                    "reference_index": reference_index
                }
                
                # Create RNA-Seq pipeline
                username = "admin"  # In a real app, this would be the logged-in user
                jobs = job_service.create_rna_seq_pipeline(
                    sample_id=sample.id,
                    sra_accession=sra_accession,
                    username=username,
                    parameters=parameters
                )
                
                st.success(f"RNA-Seq pipeline created with {len(jobs)} jobs for sample {sample.name}!")
                return True
                
            except Exception as e:
                st.error(f"Error creating pipeline: {str(e)}")
                return False
                
        return False

# Main pages
if page == "Sample Management":
    st.header("Sample Management")
    
    # Tabs for different actions
    tab1, tab2 = st.tabs(["Sample List", "Create Sample"])
    
    with tab1:
        st.subheader("All Samples")
        
        # Get all samples
        samples = sample_service.get_all_samples()
        non_container_samples = [s for s in samples if not s.is_container]
        
        if non_container_samples:
            # Convert to DataFrame for display
            samples_data = []
            for sample in non_container_samples:
                container_name = ""
                if sample.container_id:
                    container = sample_service.get_sample(sample.container_id)
                    if container:
                        container_name = container.name
                
                samples_data.append({
                    "ID": sample.sample_id,
                    "Name": sample.name,
                    "Type": sample.sample_type,
                    "Container": container_name,
                    "Barcode": sample.barcode or "",
                    "Created": sample.created_at.strftime("%Y-%m-%d"),
                    "Actions": sample.id
                })
            
            df = pd.DataFrame(samples_data)
            
            # Display as table with action buttons
            for i, row in df.iterrows():
                col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 2, 1, 1, 1, 1, 1])
                with col1:
                    st.write(row["ID"])
                with col2:
                    st.write(row["Name"])
                with col3:
                    st.write(row["Type"])
                with col4:
                    st.write(row["Container"])
                with col5:
                    st.write(row["Barcode"])
                with col6:
                    st.write(row["Created"])
                with col7:
                    sample_id = row["Actions"]
                    if st.button("Edit", key=f"edit_{sample_id}"):
                        st.session_state["edit_sample"] = sample_id
                
            # Handle edit action
            if "edit_sample" in st.session_state:
                sample_id = st.session_state["edit_sample"]
                sample = sample_service.get_sample(sample_id)
                if sample:
                    st.subheader(f"Edit Sample: {sample.name}")
                    if sample_form(sample):
                        # Clear edit state after successful update
                        del st.session_state["edit_sample"]
                        st.experimental_rerun()
        else:
            st.info("No samples found. Create a new sample to get started.")
    
    with tab2:
        if sample_form():
            st.experimental_rerun()

elif page == "Container Management":
    st.header("Container Management")
    
    # Tabs for different actions
    tab1, tab2 = st.tabs(["Container List", "Create Container"])
    
    with tab1:
        st.subheader("All Containers")
        
        # Get all containers
        containers = sample_service.get_containers()
        
        if containers:
            # Convert to DataFrame for display
            containers_data = []
            for container in containers:
                parent_name = ""
                if container.container_id:
                    parent = sample_service.get_sample(container.container_id)
                    if parent:
                        parent_name = parent.name
                        
                contained_samples = len(container.contained_sample_ids)
                
                containers_data.append({
                    "ID": container.sample_id,
                    "Name": container.name,
                    "Type": container.metadata.get("container_type", ""),
                    "Contents": f"{contained_samples} samples",
                    "Parent": parent_name,
                    "Barcode": container.barcode or "",
                    "Actions": container.id
                })
            
            df = pd.DataFrame(containers_data)
            
            # Display as table with action buttons
            for i, row in df.iterrows():
                col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 2, 1, 1, 1, 1, 1])
                with col1:
                    st.write(row["ID"])
                with col2:
                    st.write(row["Name"])
                with col3:
                    st.write(row["Type"])
                with col4:
                    st.write(row["Contents"])
                with col5:
                    st.write(row["Parent"])
                with col6:
                    st.write(row["Barcode"])
                with col7:
                    container_id = row["Actions"]
                    if st.button("Edit", key=f"edit_{container_id}"):
                        st.session_state["edit_container"] = container_id
                    if st.button("View", key=f"view_{container_id}"):
                        st.session_state["view_container"] = container_id
            
            # Handle edit action
            if "edit_container" in st.session_state:
                container_id = st.session_state["edit_container"]
                container = sample_service.get_sample(container_id)
                if container:
                    st.subheader(f"Edit Container: {container.name}")
                    if container_form(container):
                        # Clear edit state after successful update
                        del st.session_state["edit_container"]
                        st.experimental_rerun()
            
            # Handle view action
            if "view_container" in st.session_state:
                container_id = st.session_state["view_container"]
                container = sample_service.get_sample(container_id)
                if container:
                    st.subheader(f"Container: {container.name}")
                    
                    # Container details
                    container_type = container.metadata.get("container_type", "Unknown")
                    st.write(f"**Type:** {container_type}")
                    
                    if "rows" in container.metadata and "columns" in container.metadata:
                        st.write(f"**Dimensions:** {container.metadata['rows']} rows × {container.metadata['columns']} columns")
                    
                    if container.barcode:
                        st.write(f"**Barcode:** {container.barcode}")
                    
                    # List samples in this container
                    st.subheader("Contained Samples")
                    contained_samples = []
                    for sample_id in container.contained_sample_ids:
                        sample = sample_service.get_sample(sample_id)
                        if sample:
                            contained_samples.append({
                                "ID": sample.sample_id,
                                "Name": sample.name,
                                "Type": sample.sample_type,
                                "Barcode": sample.barcode or ""
                            })
                    
                    if contained_samples:
                        samples_df = pd.DataFrame(contained_samples)
                        st.dataframe(samples_df)
                    else:
                        st.info("This container is empty.")
                    
                    if st.button("Close"):
                        del st.session_state["view_container"]
                        st.experimental_rerun()
        else:
            st.info("No containers found. Create a new container to get started.")
    
    with tab2:
        if container_form():
            st.experimental_rerun()

elif page == "Sample Network":
    st.header("Sample Network Visualization")
    
    # Create sample network visualization
    samples = sample_service.get_all_samples()
    
    if samples:
        st.write("Network of sample relationships and container hierarchy:")
        
        # Create network
        G = create_sample_network(samples)
        
        # Draw network using matplotlib (static) or pyvis (interactive)
        use_interactive = st.checkbox("Use interactive visualization", value=True)
        
        if use_interactive:
            # Interactive visualization with pyvis
            html_string = draw_network_pyvis(G)
            st.components.v1.html(html_string, height=600)
        else:
            # Static visualization with matplotlib
            fig, pos = draw_network_matplotlib(G)
            st.pyplot(fig)
    else:
        st.info("No samples found. Create samples to visualize their network.")

elif page == "Bioinformatics Pipeline":
    st.header("Bioinformatics Pipeline")
    
    # Tabs for different actions
    tab1, tab2 = st.tabs(["Create Pipeline", "Pipeline Status"])
    
    with tab1:
        if rna_seq_form():
            st.experimental_rerun()
    
    with tab2:
        st.subheader("RNA-Seq Pipelines")
        
        # Get all samples with RNA-Seq analyses
        samples = sample_service.get_all_samples()
        samples_with_rnaseq = []
        
        for sample in samples:
            analyses = sample.get_analyses(analysis_type="rna-seq")
            if analyses:
                for analysis in analyses:
                    samples_with_rnaseq.append({
                        "sample": sample,
                        "analysis": analysis
                    })
        
        if samples_with_rnaseq:
            # Display pipelines
            for item in samples_with_rnaseq:
                sample = item["sample"]
                analysis = item["analysis"]
                
                with st.expander(f"{sample.name} - {analysis['sra_accession']}"):
                    st.write(f"**Sample:** {sample.name} ({sample.sample_id})")
                    st.write(f"**SRA Accession:** {analysis['sra_accession']}")
                    st.write(f"**Created:** {analysis['created_at']}")
                    st.write(f"**Status:** {analysis['status']}")
                    
                    # Get pipeline jobs
                    job_ids = analysis.get('pipeline_jobs', [])
                    if job_ids:
                        st.subheader("Pipeline Jobs")
                        
                        jobs_data = []
                        for job_id in job_ids:
                            job = job_service.get_job(job_id)
                            if job:
                                # Calculate duration if available
                                duration = ""
                                if job.start_time:
                                    if job.end_time:
                                        duration = str(timedelta(seconds=job.get_duration())).split('.')[0]
                                    else:
                                        duration = str(timedelta(seconds=job.get_duration())).split('.')[0] + " (running)"
                                
                                jobs_data.append({
                                    "Name": job.name,
                                    "Type": job.job_type.value,
                                    "Status": job.status.value,
                                    "Started": job.start_time.strftime("%Y-%m-%d %H:%M") if job.start_time else "",
                                    "Duration": duration,
                                    "ID": str(job.id)
                                })
                        
                        if jobs_data:
                            jobs_df = pd.DataFrame(jobs_data)
                            st.dataframe(jobs_df)
                            
                            # Add action buttons
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Refresh Status", key=f"refresh_{sample.id}_{analysis['sra_accession']}"):
                                    st.info("Refreshing job statuses... (not implemented yet)")
                            with col2:
                                if st.button("View Jobs Detail", key=f"view_{sample.id}_{analysis['sra_accession']}"):
                                    st.session_state["view_pipeline_jobs"] = job_ids
                    else:
                        st.info("No jobs found for this pipeline.")
            
            # Handle view jobs detail action
            if "view_pipeline_jobs" in st.session_state:
                job_ids = st.session_state["view_pipeline_jobs"]
                st.subheader("Pipeline Jobs Detail")
                
                jobs = []
                for job_id in job_ids:
                    job = job_service.get_job(job_id)
                    if job:
                        jobs.append(job)
                
                if jobs:
                    # Display detailed job information
                    for job in jobs:
                        with st.expander(f"{job.name} ({job.job_type.value})"):
                            st.write(f"**Status:** {job.status.value}")
                            st.write(f"**Created by:** {job.created_by}")
                            st.write(f"**Created at:** {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                            
                            if job.start_time:
                                st.write(f"**Started at:** {job.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            
                            if job.end_time:
                                st.write(f"**Ended at:** {job.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                                st.write(f"**Duration:** {str(timedelta(seconds=job.get_duration())).split('.')[0]}")
                            
                            if job.description:
                                st.write(f"**Description:** {job.description}")
                            
                            if job.parameters:
                                st.write("**Parameters:**")
                                params_df = pd.DataFrame([{"Parameter": k, "Value": v} for k, v in job.parameters.items()])
                                st.dataframe(params_df)
                            
                            if job.aws_job_id:
                                st.write(f"**AWS Job ID:** {job.aws_job_id}")
                            
                            if job.log_url:
                                st.write(f"**Log URL:** [View Logs]({job.log_url})")
                            
                            # Display input and output files
                            if job.input_files:
                                st.write("**Input Files:**")
                                input_df = pd.DataFrame(job.input_files)
                                st.dataframe(input_df)
                            
                            if job.output_files:
                                st.write("**Output Files:**")
                                output_df = pd.DataFrame(job.output_files)
                                st.dataframe(output_df)
                                
                            # Display job dependencies
                            if job.parent_job_ids:
                                parent_names = []
                                for parent_id in job.parent_job_ids:
                                    parent_job = job_service.get_job(parent_id)
                                    if parent_job:
                                        parent_names.append(f"{parent_job.name} ({parent_job.job_type.value})")
                                    else:
                                        parent_names.append(f"Unknown ({parent_id})")
                                
                                st.write("**Dependencies:**")
                                st.write(", ".join(parent_names))
                
                if st.button("Close"):
                    del st.session_state["view_pipeline_jobs"]
                    st.experimental_rerun()
        else:
            st.info("No RNA-Seq pipelines found. Create a new pipeline to get started.")

elif page == "Batch Processing":
    st.header("Batch Processing")
    
    st.markdown("""
    Select samples that have read files, and run AWS Batch jobs on them.
    The input will be the selected read files and the output will be processed reads.
    """)
    
    # Get all samples with files
    all_samples = sample_service.get_all_samples()
    samples_with_files = []
    
    # Find samples that have read files
    for sample in all_samples:
        if not sample.is_container and sample.file_paths:
            read_files = detect_read_files(sample)
            if any(read_files.values()):  # Has at least one read file
                samples_with_files.append({
                    "sample": sample,
                    "read_files": read_files
                })
    
    if not samples_with_files:
        st.warning("No samples with read files found. Please add read files to your samples first.")
    else:
        # Sample selection
        st.subheader("Select Samples")
        
        # Create a selection table with checkboxes
        selected_samples = []
        for item in samples_with_files:
            sample = item["sample"]
            read_files = item["read_files"]
            
            # Calculate total read files
            total_reads = len(read_files["single_end"]) + len(read_files["paired_end_1"]) + len(read_files["paired_end_2"])
            
            col1, col2, col3, col4 = st.columns([0.1, 0.3, 0.3, 0.3])
            with col1:
                selected = st.checkbox("", key=f"select_{sample.id}")
                if selected:
                    selected_samples.append(item)
            with col2:
                st.write(f"**{sample.name}** ({sample.sample_id})")
            with col3:
                st.write(f"Type: {sample.sample_type}")
            with col4:
                st.write(f"Read files: {total_reads}")
        
        if selected_samples:
            st.subheader("Process Selected Samples")
            
            # Job type selection
            job_type = st.selectbox(
                "Select Processing Type",
                options=[
                    "READ_PROCESSING", "NORMALIZATION", "QUANTIFICATION", 
                    "ASSEMBLY", "ANNOTATION", "FASTQC"
                ]
            )
            
            # Parameters based on job type
            st.subheader("Job Parameters")
            parameters = {}
            
            if job_type == "READ_PROCESSING":
                col1, col2 = st.columns(2)
                with col1:
                    parameters["rrna_reference"] = st.text_input(
                        "rRNA Reference Path",
                        value="references/rrna/rrna_reference.fa"
                    )
                with col2:
                    parameters["output_prefix"] = st.text_input(
                        "Output Prefix",
                        value="processed_reads"
                    )
            
            elif job_type == "NORMALIZATION":
                col1, col2 = st.columns(2)
                with col1:
                    parameters["target_depth"] = st.number_input(
                        "Target Depth",
                        min_value=1,
                        value=100
                    )
                with col2:
                    parameters["min_depth"] = st.number_input(
                        "Minimum Depth",
                        min_value=1,
                        value=5
                    )
                    parameters["output_prefix"] = st.text_input(
                        "Output Prefix",
                        value="normalized_reads"
                    )
            
            elif job_type == "QUANTIFICATION":
                parameters["reference_index"] = st.text_input(
                    "Reference Index Path",
                    value="references/transcriptome/index"
                )
                parameters["output_prefix"] = st.text_input(
                    "Output Prefix",
                    value="quant_results"
                )
            
            elif job_type == "ASSEMBLY":
                parameters["memory_limit"] = st.number_input(
                    "Memory Limit (GB)",
                    min_value=4,
                    max_value=64,
                    value=32
                )
                parameters["output_prefix"] = st.text_input(
                    "Output Prefix",
                    value="assembly_results"
                )
            
            elif job_type == "ANNOTATION":
                parameters["eggnog_db_path"] = st.text_input(
                    "EggNOG Database Path",
                    value="references/eggnog"
                )
                parameters["output_prefix"] = st.text_input(
                    "Output Prefix",
                    value="annotation_results"
                )
            
            elif job_type == "FASTQC":
                parameters["output_prefix"] = st.text_input(
                    "Output Prefix",
                    value="fastqc_results"
                )
            
            # Submit button
            if st.button("Submit Jobs"):
                jobs_created = []
                for item in selected_samples:
                    sample = item["sample"]
                    read_files = item["read_files"]
                    
                    try:
                        # Create a new job for this sample
                        job_data = {
                            "name": f"{job_type} for {sample.name}",
                            "job_type": job_type,
                            "sample_id": str(sample.id),
                            "created_by": "admin",  # In a real app, this would be the logged-in user
                            "parameters": parameters,
                            "description": f"Processing {sample.name} with {job_type}"
                        }
                        
                        # Add read files as input
                        input_files = []
                        if read_files["single_end"]:
                            for path in read_files["single_end"]:
                                input_files.append({"path": path, "description": "Single-end reads"})
                        
                        if read_files["paired_end_1"] and read_files["paired_end_2"]:
                            for idx, (r1, r2) in enumerate(zip(read_files["paired_end_1"], read_files["paired_end_2"])):
                                input_files.append({"path": r1, "description": f"Paired-end reads R1 (pair {idx+1})"})
                                input_files.append({"path": r2, "description": f"Paired-end reads R2 (pair {idx+1})"})
                        
                        # Create job with input files
                        job_data["input_files"] = input_files
                        job = job_service.create_job(job_data)
                        jobs_created.append(job)
                        
                        # Submit job to AWS Batch (if configured)
                        try:
                            result = job_service.submit_job_to_aws(job.id)
                            st.success(f"Job for {sample.name} submitted to AWS Batch: {result['aws_job_id']}")
                        except Exception as e:
                            st.warning(f"Job created but couldn't be submitted to AWS Batch: {str(e)}")
                            st.info("Configure AWS credentials and retry submission from the Job Dashboard.")
                        
                    except Exception as e:
                        st.error(f"Error creating job for sample {sample.name}: {str(e)}")
                
                if jobs_created:
                    st.success(f"Created {len(jobs_created)} jobs successfully!")
                    st.balloons()
                    
                    # Provide link to Job Dashboard
                    st.markdown("[Go to Job Dashboard to view jobs](#job-dashboard)")

elif page == "Job Dashboard":
    st.header("Job Dashboard")
    
    # Add auto-refresh option
    auto_refresh = st.checkbox("Auto-refresh (every 30 seconds)", value=False)
    if auto_refresh:
        if "last_refresh" not in st.session_state:
            st.session_state["last_refresh"] = time.time()
        
        if time.time() - st.session_state["last_refresh"] > 30:
            st.session_state["last_refresh"] = time.time()
            st.experimental_rerun()
    
    # Display job statistics
    all_jobs = job_service.get_all_jobs()
    
    if all_jobs:
        # Job statistics
        jobs_by_status = {}
        for status in JobStatus:
            jobs_by_status[status.value] = len(job_service.get_jobs_by_status(status))
        
        jobs_by_type = {}
        for job_type in JobType:
            type_jobs = [job for job in all_jobs if job.job_type == job_type]
            if type_jobs:
                jobs_by_type[job_type.value] = len(type_jobs)
        
        # Display job statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("Jobs by Status")
            status_df = pd.DataFrame({
                "Status": list(jobs_by_status.keys()),
                "Count": list(jobs_by_status.values())
            })
            st.dataframe(status_df)
        
        with col2:
            st.subheader("Jobs by Type")
            type_df = pd.DataFrame({
                "Type": list(jobs_by_type.keys()),
                "Count": list(jobs_by_type.values())
            })
            st.dataframe(type_df)
        
        with col3:
            st.subheader("Recent Jobs")
            # Get jobs from the last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            recent_jobs = [job for job in all_jobs if job.created_at > yesterday]
            st.write(f"Last 24 hours: {len(recent_jobs)} jobs")
            
            # Get jobs from the last week
            last_week = datetime.now() - timedelta(days=7)
            week_jobs = [job for job in all_jobs if job.created_at > last_week]
            st.write(f"Last 7 days: {len(week_jobs)} jobs")
            
            st.write(f"Total jobs: {len(all_jobs)}")
        
        # Tabs for different job views
        tab1, tab2, tab3 = st.tabs(["Active Jobs", "Completed Jobs", "All Jobs"])
        
        with tab1:
            active_jobs = [job for job in all_jobs if job.status in [JobStatus.PENDING, JobStatus.SUBMITTED, JobStatus.RUNNING]]
            if active_jobs:
                active_data = []
                for job in active_jobs:
                    sample = sample_service.get_sample(job.sample_id)
                    sample_name = sample.name if sample else "Unknown"
                    
                    # Calculate duration if started
                    duration = ""
                    if job.start_time:
                        duration = str(timedelta(seconds=job.get_duration())).split('.')[0]
                    
                    active_data.append({
                        "Job Name": job.name,
                        "Type": job.job_type.value,
                        "Sample": sample_name,
                        "Status": job.status.value,
                        "Started": job.start_time.strftime("%Y-%m-%d %H:%M") if job.start_time else "",
                        "Duration": duration,
                        "ID": str(job.id)
                    })
                
                active_df = pd.DataFrame(active_data)
                st.dataframe(active_df)
                
                if st.button("Refresh Active Jobs"):
                    st.session_state["last_refresh"] = time.time()
                    st.experimental_rerun()
            else:
                st.info("No active jobs.")
        
        with tab2:
            completed_jobs = [job for job in all_jobs if job.status in [JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED]]
            if completed_jobs:
                # Sort by end time (most recent first)
                completed_jobs.sort(key=lambda j: j.end_time if j.end_time else datetime.min, reverse=True)
                
                completed_data = []
                for job in completed_jobs:
                    sample = sample_service.get_sample(job.sample_id)
                    sample_name = sample.name if sample else "Unknown"
                    
                    # Calculate duration
                    duration = ""
                    if job.start_time and job.end_time:
                        duration = str(timedelta(seconds=job.get_duration())).split('.')[0]
                    
                    completed_data.append({
                        "Job Name": job.name,
                        "Type": job.job_type.value,
                        "Sample": sample_name,
                        "Status": job.status.value,
                        "Completed": job.end_time.strftime("%Y-%m-%d %H:%M") if job.end_time else "",
                        "Duration": duration,
                        "ID": str(job.id)
                    })
                
                completed_df = pd.DataFrame(completed_data)
                st.dataframe(completed_df)
            else:
                st.info("No completed jobs.")
        
        with tab3:
            all_jobs_data = []
            for job in all_jobs:
                sample = sample_service.get_sample(job.sample_id)
                sample_name = sample.name if sample else "Unknown"
                
                # Format timestamps
                created = job.created_at.strftime("%Y-%m-%d %H:%M")
                started = job.start_time.strftime("%Y-%m-%d %H:%M") if job.start_time else ""
                ended = job.end_time.strftime("%Y-%m-%d %H:%M") if job.end_time else ""
                
                # Calculate duration
                duration = ""
                if job.start_time:
                    if job.end_time:
                        duration = str(timedelta(seconds=job.get_duration())).split('.')[0]
                    else:
                        duration = str(timedelta(seconds=job.get_duration())).split('.')[0] + " (running)"
                
                all_jobs_data.append({
                    "Job Name": job.name,
                    "Type": job.job_type.value,
                    "Sample": sample_name,
                    "Status": job.status.value,
                    "Created": created,
                    "Started": started,
                    "Ended": ended,
                    "Duration": duration,
                    "ID": str(job.id)
                })
            
            all_jobs_df = pd.DataFrame(all_jobs_data)
            st.dataframe(all_jobs_df)
            
            # Job detail view
            job_id = st.selectbox("Select a job to view details:", options=["None"] + [str(job.id) for job in all_jobs])
            if job_id != "None":
                job = job_service.get_job(job_id)
                if job:
                    st.subheader(f"Job Details: {job.name}")
                    
                    # Job details
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Type:** {job.job_type.value}")
                        st.write(f"**Status:** {job.status.value}")
                        st.write(f"**Created by:** {job.created_by}")
                        st.write(f"**Created at:** {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    with col2:
                        sample = sample_service.get_sample(job.sample_id)
                        sample_name = sample.name if sample else "Unknown"
                        st.write(f"**Sample:** {sample_name}")
                        
                        if job.start_time:
                            st.write(f"**Started at:** {job.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        if job.end_time:
                            st.write(f"**Ended at:** {job.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            st.write(f"**Duration:** {str(timedelta(seconds=job.get_duration())).split('.')[0]}")
                    
                    if job.description:
                        st.write(f"**Description:** {job.description}")
                    
                    if job.aws_job_id:
                        st.write(f"**AWS Job ID:** {job.aws_job_id}")
                        st.write(f"**AWS Job Definition:** {job.aws_job_definition}")
                    
                    # Job parameters
                    if job.parameters:
                        st.subheader("Parameters")
                        params_df = pd.DataFrame([{"Parameter": k, "Value": v} for k, v in job.parameters.items()])
                        st.dataframe(params_df)
                    
                    # Job files
                    col1, col2 = st.columns(2)
                    with col1:
                        if job.input_files:
                            st.subheader("Input Files")
                            input_df = pd.DataFrame(job.input_files)
                            st.dataframe(input_df)
                    
                    with col2:
                        if job.output_files:
                            st.subheader("Output Files")
                            output_df = pd.DataFrame(job.output_files)
                            st.dataframe(output_df)
                    
                    # Job dependencies
                    col1, col2 = st.columns(2)
                    with col1:
                        if job.parent_job_ids:
                            st.subheader("Parent Jobs")
                            parent_data = []
                            for parent_id in job.parent_job_ids:
                                parent_job = job_service.get_job(parent_id)
                                if parent_job:
                                    parent_data.append({
                                        "Name": parent_job.name,
                                        "Type": parent_job.job_type.value,
                                        "Status": parent_job.status.value,
                                        "ID": str(parent_job.id)
                                    })
                                else:
                                    parent_data.append({
                                        "Name": "Unknown",
                                        "Type": "",
                                        "Status": "",
                                        "ID": str(parent_id)
                                    })
                            
                            parent_df = pd.DataFrame(parent_data)
                            st.dataframe(parent_df)
                    
                    with col2:
                        if job.child_job_ids:
                            st.subheader("Child Jobs")
                            child_data = []
                            for child_id in job.child_job_ids:
                                child_job = job_service.get_job(child_id)
                                if child_job:
                                    child_data.append({
                                        "Name": child_job.name,
                                        "Type": child_job.job_type.value,
                                        "Status": child_job.status.value,
                                        "ID": str(child_job.id)
                                    })
                                else:
                                    child_data.append({
                                        "Name": "Unknown",
                                        "Type": "",
                                        "Status": "",
                                        "ID": str(child_id)
                                    })
                            
                            child_df = pd.DataFrame(child_data)
                            st.dataframe(child_df)
    else:
        st.info("No jobs found. Create a pipeline to generate jobs.")