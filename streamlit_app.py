"""BLIMS - Streamlit GUI Application."""

import streamlit as st
import networkx as nx
from pyvis.network import Network
import tempfile
from uuid import UUID, uuid4
import json
import os
from typing import Any, Dict, List, Optional

from blims.core.service import SampleService
from blims.core.repository import SampleRepository
from blims.models.sample import Sample
from test_data import create_test_data

# Page configuration - MUST be the first Streamlit command
st.set_page_config(
    page_title="BLIMS - Sample Management",
    page_icon="🧪",
    layout="wide",
)

# Initialize the service with a persistent repository
@st.cache_resource
def get_service():
    service = SampleService()
    # Create test data if no samples exist
    if not service.repository.get_all():
        create_test_data(service)
    return service

service = get_service()

# Sidebar navigation
st.sidebar.title("BLIMS")
st.sidebar.subheader("Biolab Laboratory Information Management System")

page = st.sidebar.radio(
    "Navigation",
    ["Samples Dashboard", "Create Sample", "Connect Samples", "Container Management", "Sample Details"]
)

# Helper functions
def get_sample_options():
    samples = service.repository.get_all()
    options = {}
    for sample in samples:
        options[f"{sample.name} ({sample.sample_id})"] = sample.id
    return options

def get_sample_icon(sample_type, is_container):
    """Get an emoji icon for a sample type.
    
    Args:
        sample_type: The type of the sample
        is_container: Whether the sample is a container
        
    Returns:
        An emoji icon representing the sample type
    """
    # First check if it's a container
    if is_container:
        container_icons = {
            "Plate": "🧫",  # Petri dish for plate
            "Box": "📦",    # Box
            "Rack": "🗄️",   # Cabinet for rack
            "Freezer": "❄️", # Snowflake for freezer
        }
        return container_icons.get(sample_type, "📦")  # Default to box
    
    # Regular sample types
    sample_icons = {
        "Blood": "🩸",      # Blood drop
        "Tissue": "🧠",     # Brain for tissue (approximation)
        "DNA": "🧬",        # DNA
        "RNA": "🧬",        # DNA (same as DNA)
        "PCR": "🧪",        # Test tube
        "Protein": "🔬",    # Microscope
        "Cell": "🦠",       # Microbe
    }
    return sample_icons.get(sample_type, "🧪")  # Default to test tube

def load_sample_network():
    """Create a network visualization of samples and their relationships."""
    samples = service.repository.get_all()
    
    # Create a graph
    G = nx.DiGraph()
    
    # Add nodes for each sample
    for sample in samples:
        # Get appropriate icon
        icon = get_sample_icon(sample.sample_type, sample.is_container)
        
        G.add_node(
            str(sample.id), 
            label=f"{icon} {sample.sample_id}: {sample.name}", 
            title=f"Type: {sample.sample_type}\nBarcode: {sample.barcode or 'None'}", 
            group=sample.sample_type
        )
    
    # Add edges for parent-child relationships
    for sample in samples:
        for parent_id in sample.parent_ids:
            G.add_edge(str(parent_id), str(sample.id), title="derives from", arrows="to", color="blue")
    
    # Add edges for container relationships
    for sample in samples:
        for contained_id in sample.contained_sample_ids:
            G.add_edge(str(sample.id), str(contained_id), title="contains", color="red", arrows="to", dashes=True)
    
    # Create a pyvis network
    net = Network(height="600px", width="100%", directed=True, notebook=False)
    
    # Add nodes and edges
    net.from_nx(G)
    
    # Set options
    net.toggle_physics(True)
    net.set_options("""
    {
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 100,
                "springConstant": 0.08
            },
            "solver": "forceAtlas2Based",
            "stabilization": {
                "iterations": 100
            }
        },
        "interaction": {
            "navigationButtons": true,
            "keyboard": true,
            "hover": true
        },
        "edges": {
            "smooth": {
                "type": "continuous",
                "forceDirection": "none"
            },
            "arrows": {
                "to": {
                    "enabled": true,
                    "scaleFactor": 0.5
                }
            }
        },
        "nodes": {
            "font": {
                "size": 16,
                "face": "arial"
            },
            "shape": "box",
            "shadow": true
        }
    }
    """)
    
    # Save and display the network
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmp:
        net.save_graph(tmp.name)
        with open(tmp.name, 'r', encoding='utf-8') as f:
            html_string = f.read()
    
    os.unlink(tmp.name)
    return html_string

# Page content
if page == "Samples Dashboard":
    st.title("Samples Dashboard")
    
    # Sample statistics
    samples = service.repository.get_all()
    sample_types = {}
    for sample in samples:
        if sample.sample_type in sample_types:
            sample_types[sample.sample_type] += 1
        else:
            sample_types[sample.sample_type] = 1
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Samples", len(samples))
        
        # Sample types
        st.subheader("Sample Types")
        for sample_type, count in sample_types.items():
            st.write(f"- {sample_type}: {count}")
    
    # Network visualization of samples
    st.subheader("Sample Network")
    if samples:
        html_string = load_sample_network()
        st.components.v1.html(html_string, height=600)
    else:
        st.info("No samples available. Create some samples to see the network visualization.")
    
    # Show sample type icons legend
    st.subheader("Sample Type Icons")
    legend_col1, legend_col2, legend_col3 = st.columns(3)
    
    with legend_col1:
        st.markdown("**Regular Samples:**")
        st.markdown("🩸 Blood")
        st.markdown("🧠 Tissue")
        st.markdown("🧬 DNA/RNA")
        st.markdown("🧪 PCR/General")
        
    with legend_col2:
        st.markdown("**Containers:**")
        st.markdown("📦 Box/General Container")
        st.markdown("🧫 Plate")
        st.markdown("🗄️ Rack")
        st.markdown("❄️ Freezer")
        
    with legend_col3:
        st.markdown("**Edge Colors:**")
        st.markdown("🔵 Blue: Parent-Child")
        st.markdown("🔴 Red: Container-Contained")
    
    # Sample list
    st.subheader("All Samples")
    # Add search filter
    search_term = st.text_input("🔍 Search Samples", placeholder="Filter by name, type, or barcode...")
    
    if samples:
        sample_data = []
        for sample in samples:
            # Format parent samples
            parent_names = []
            for parent_id in sample.parent_ids:
                parent = service.repository.get(UUID(parent_id) if isinstance(parent_id, str) else parent_id)
                if parent:
                    parent_names.append(parent.name)
            
            # Format container
            container_name = None
            if sample.container_id:
                container = service.repository.get(UUID(sample.container_id) if isinstance(sample.container_id, str) else sample.container_id)
                if container:
                    container_name = container.name
            
            sample_data.append({
                "ID": sample.sample_id,
                "Barcode": sample.barcode or "N/A",
                "Name": sample.name,
                "Type": sample.sample_type,
                "Container": container_name or "None",
                "Is Container": "Yes" if sample.is_container else "No",
                "Created By": sample.created_by,
                "Parents": ", ".join(parent_names) if parent_names else "None", 
                "Files": len(sample.file_paths),
                "Metadata": len(sample.metadata)
            })
        
        # Filter samples if search term is provided
        if search_term:
            search_term = search_term.lower()
            filtered_data = [
                s for s in sample_data 
                if search_term in s["Name"].lower() 
                or search_term in s["Type"].lower() 
                or search_term in s["Barcode"].lower()
                or search_term in s["ID"].lower()
            ]
            if filtered_data:
                st.dataframe(filtered_data, use_container_width=True)
                st.caption(f"Showing {len(filtered_data)} of {len(sample_data)} samples")
            else:
                st.info(f"No samples match the search term '{search_term}'")
                st.dataframe(sample_data, use_container_width=True)
        else:
            st.dataframe(sample_data, use_container_width=True)
    else:
        st.info("No samples available. Create a sample to get started.")

elif page == "Create Sample":
    st.title("Create Sample")
    
    # Button to show the create sample form
    with st.expander("Create New Sample", expanded=True):
        tab1, tab2 = st.tabs(["Basic Sample", "Container"])
        
        with tab1:
            # Basic sample creation form
            with st.form("create_sample_form"):
                st.subheader("Required Fields")
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("Sample Name *", key="create_name")
                with col2:
                    sample_type = st.text_input("Sample Type *", key="create_type")
                
                created_by = st.text_input("Created By *", key="create_by")
                barcode = st.text_input("Barcode (Optional)", key="create_barcode", 
                                       help="Unique identifier for scanning and tracking")
                
                st.subheader("Metadata")
                metadata_count = st.number_input("Number of metadata fields", min_value=0, max_value=10, value=1)
                metadata = {}
                
                for i in range(metadata_count):
                    col1, col2 = st.columns(2)
                    with col1:
                        key = st.text_input(f"Key {i+1}", key=f"meta_key_{i}")
                    with col2:
                        value = st.text_input(f"Value {i+1}", key=f"meta_value_{i}")
                    
                    if key:
                        metadata[key] = value
                
                # Parent samples
                st.subheader("Parent Samples")
                sample_options = get_sample_options()
                
                parent_ids = []
                if sample_options:
                    parent_count = st.number_input("Number of parent samples", min_value=0, max_value=len(sample_options), value=0)
                    
                    for i in range(parent_count):
                        parent = st.selectbox(f"Parent Sample {i+1}", options=list(sample_options.keys()), key=f"parent_{i}")
                        if parent:
                            parent_ids.append(UUID(sample_options[parent]))
                else:
                    st.info("No existing samples to select as parents.")
                
                # Files
                st.subheader("Files")
                file_count = st.number_input("Number of files", min_value=0, max_value=5, value=0)
                file_paths = []
                
                for i in range(file_count):
                    file_path = st.text_input(f"File Path {i+1}", key=f"file_{i}")
                    if file_path:
                        file_paths.append(file_path)
                
                st.markdown("**Fields marked with * are required**")
                submitted = st.form_submit_button("Create Sample")
                
                if submitted:
                    # Validate required fields
                    if not name or not sample_type or not created_by:
                        st.error("Please fill in all required fields (marked with *).")
                    else:
                        try:
                            sample = service.create_sample(
                                name=name,
                                sample_type=sample_type,
                                created_by=created_by,
                                metadata=metadata,
                                parent_ids=parent_ids,
                                file_paths=file_paths,
                                barcode=barcode,
                                is_container=False
                            )
                            
                            st.success(f"Sample '{name}' created successfully with ID: {sample.sample_id}")
                        except ValueError as e:
                            st.error(f"Error creating sample: {str(e)}")
        
        with tab2:
            # Container creation form
            with st.form("create_container_form"):
                st.subheader("Required Fields")
                col1, col2 = st.columns(2)
                with col1:
                    container_name = st.text_input("Container Name *", key="container_name")
                with col2:
                    container_type = st.selectbox("Container Type *", 
                                                options=["Plate", "Box", "Rack", "Freezer", "Other"],
                                                key="container_type")
                    if container_type == "Other":
                        container_type = st.text_input("Specify Container Type *", key="container_type_other")
                
                container_created_by = st.text_input("Created By *", key="container_created_by")
                container_barcode = st.text_input("Barcode (Optional)", key="container_barcode",
                                                help="Unique identifier for scanning and tracking")
                
                # Container metadata
                st.subheader("Container Properties")
                container_metadata = {}
                
                col1, col2 = st.columns(2)
                with col1:
                    container_capacity = st.text_input("Capacity", key="container_capacity", 
                                                     placeholder="e.g., 96 wells, 81 slots")
                    if container_capacity:
                        container_metadata["capacity"] = container_capacity
                
                with col2:
                    container_manufacturer = st.text_input("Manufacturer", key="container_manufacturer")
                    if container_manufacturer:
                        container_metadata["manufacturer"] = container_manufacturer
                
                # Additional container metadata
                custom_metadata_count = st.number_input("Number of additional properties", min_value=0, max_value=5, value=0)
                
                for i in range(custom_metadata_count):
                    col1, col2 = st.columns(2)
                    with col1:
                        custom_key = st.text_input(f"Property {i+1}", key=f"container_meta_key_{i}")
                    with col2:
                        custom_value = st.text_input(f"Value {i+1}", key=f"container_meta_value_{i}")
                    
                    if custom_key:
                        container_metadata[custom_key] = custom_value
                
                # Contents
                st.subheader("Initial Contents")
                container_sample_options = get_sample_options()
                
                contained_sample_ids = []
                if container_sample_options:
                    content_count = st.number_input("Number of samples to add", min_value=0, max_value=len(container_sample_options), value=0)
                    
                    for i in range(content_count):
                        content = st.selectbox(f"Sample {i+1}", options=list(container_sample_options.keys()), key=f"content_{i}")
                        if content:
                            contained_sample_ids.append(UUID(container_sample_options[content]))
                
                st.markdown("**Fields marked with * are required**")
                container_submitted = st.form_submit_button("Create Container")
                
                if container_submitted:
                    # Validate required fields
                    if not container_name or not container_type or not container_created_by:
                        st.error("Please fill in all required fields (marked with *).")
                    else:
                        try:
                            container = service.create_sample(
                                name=container_name,
                                sample_type=container_type,
                                created_by=container_created_by,
                                metadata=container_metadata,
                                barcode=container_barcode,
                                is_container=True,
                                contained_sample_ids=contained_sample_ids
                            )
                            
                            st.success(f"Container '{container_name}' created successfully with ID: {container.sample_id}")
                        except ValueError as e:
                            st.error(f"Error creating container: {str(e)}")

elif page == "Connect Samples":
    st.title("Connect Samples")
    
    # Get sample options
    sample_options = get_sample_options()
    
    if len(sample_options) < 2:
        st.warning("You need at least 2 samples to create connections. Please create more samples.")
    else:
        tab1, tab2 = st.tabs(["Parent-Child Relationship", "Add Metadata"])
        
        with tab1:
            st.subheader("Create Parent-Child Relationship")
            
            with st.form("parent_child_form"):
                parent = st.selectbox("Parent Sample", options=list(sample_options.keys()), key="parent_select")
                child = st.selectbox("Child Sample (derived from parent)", options=list(sample_options.keys()), key="child_select")
                
                pc_submitted = st.form_submit_button("Connect Samples")
                
                if pc_submitted:
                    if parent == child:
                        st.error("Parent and child samples cannot be the same.")
                    else:
                        try:
                            parent_id = UUID(sample_options[parent])
                            child_id = UUID(sample_options[child])
                            
                            # Get the samples
                            parent_sample = service.repository.get(parent_id)
                            child_sample = service.repository.get(child_id)
                            
                            # Establish relationship
                            child_sample.add_parent(parent_id)
                            parent_sample.add_child(child_id)
                            
                            st.success(f"Connected {parent_sample.name} as parent of {child_sample.name}")
                        except ValueError as e:
                            st.error(f"Error connecting samples: {str(e)}")
        
        with tab2:
            st.subheader("Add Metadata to Sample")
            
            with st.form("add_metadata_form"):
                target_sample = st.selectbox("Select Sample", options=list(sample_options.keys()), key="metadata_sample")
                metadata_key = st.text_input("Metadata Key")
                metadata_value = st.text_input("Metadata Value")
                
                meta_submitted = st.form_submit_button("Add Metadata")
                
                if meta_submitted:
                    if not metadata_key or not metadata_value:
                        st.error("Both key and value are required.")
                    else:
                        try:
                            sample_id = UUID(sample_options[target_sample])
                            sample = service.add_metadata_to_sample(sample_id, metadata_key, metadata_value)
                            
                            st.success(f"Added metadata to {sample.name}: {metadata_key} = {metadata_value}")
                        except ValueError as e:
                            st.error(f"Error adding metadata: {str(e)}")

elif page == "Container Management":
    st.title("Container Management")
    
    sample_options = get_sample_options()
    
    if not sample_options:
        st.warning("No samples available. Create some samples first.")
    else:
        tab1, tab2 = st.tabs(["Add to Container", "Remove from Container"])
        
        with tab1:
            st.subheader("Add Sample to Container")
            
            with st.form("add_to_container_form"):
                container = st.selectbox("Container Sample", options=list(sample_options.keys()), key="container_select")
                sample_to_add = st.selectbox("Sample to Add", options=list(sample_options.keys()), key="sample_add_select")
                
                add_submitted = st.form_submit_button("Add to Container")
                
                if add_submitted:
                    if container == sample_to_add:
                        st.error("A sample cannot contain itself.")
                    else:
                        try:
                            container_id = UUID(sample_options[container])
                            sample_id = UUID(sample_options[sample_to_add])
                            
                            # Add sample to container
                            updated_container = service.add_sample_to_container(sample_id, container_id)
                            
                            st.success(f"Added {sample_to_add.split(' (')[0]} to container {container.split(' (')[0]}")
                        except ValueError as e:
                            st.error(f"Error adding to container: {str(e)}")
        
        with tab2:
            st.subheader("Remove Sample from Container")
            
            # Get only samples that are in containers
            contained_samples = {}
            for sample in service.repository.get_all():
                if sample.container_id:
                    contained_samples[f"{sample.name} ({sample.id})"] = sample.id
            
            if not contained_samples:
                st.info("No samples are currently in containers.")
            else:
                with st.form("remove_from_container_form"):
                    sample_to_remove = st.selectbox("Sample to Remove", options=list(contained_samples.keys()), key="sample_remove_select")
                    
                    remove_submitted = st.form_submit_button("Remove from Container")
                    
                    if remove_submitted:
                        try:
                            sample_id = UUID(contained_samples[sample_to_remove])
                            
                            # Remove sample from container
                            container = service.remove_sample_from_container(sample_id)
                            
                            st.success(f"Removed {sample_to_remove.split(' (')[0]} from its container")
                        except ValueError as e:
                            st.error(f"Error removing from container: {str(e)}")

elif page == "Sample Details":
    st.title("Sample Details")
    
    sample_options = get_sample_options()
    
    if not sample_options:
        st.warning("No samples available. Create some samples first.")
    else:
        selected_sample = st.selectbox("Select Sample", options=list(sample_options.keys()))
        sample_id = sample_options[selected_sample]
        # Convert to UUID only if it's a string
        if isinstance(sample_id, str):
            sample_id = UUID(sample_id)
        
        sample = service.repository.get(sample_id)
        
        if sample:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Basic Information")
                st.write(f"**ID:** {sample.sample_id}")
                st.write(f"**UUID:** {sample.id}")
                if sample.barcode:
                    st.write(f"**Barcode:** {sample.barcode}")
                st.write(f"**Name:** {sample.name}")
                st.write(f"**Type:** {sample.sample_type}")
                st.write(f"**Is Container:** {'Yes' if sample.is_container else 'No'}")
                st.write(f"**Created By:** {sample.created_by}")
                st.write(f"**Created At:** {sample.created_at}")
                
                # Container info
                if sample.container_id:
                    container = service.repository.get(sample.container_id)
                    if container:
                        st.write(f"**Container:** {container.name} ({container.sample_id})")
                else:
                    st.write("**Container:** None")
            
            with col2:
                st.subheader("Metadata")
                if sample.metadata:
                    for key, value in sample.metadata.items():
                        st.write(f"**{key}:** {value}")
                else:
                    st.write("No metadata available.")
            
            # Lineage
            st.subheader("Sample Lineage")
            
            try:
                lineage = service.get_sample_lineage(sample_id)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Ancestors:**")
                    if lineage["ancestors"]:
                        for ancestor in lineage["ancestors"]:
                            st.write(f"- {ancestor.name} ({ancestor.sample_id})")
                    else:
                        st.write("No ancestors.")
                
                with col2:
                    st.write("**Descendants:**")
                    if lineage["descendants"]:
                        for descendant in lineage["descendants"]:
                            st.write(f"- {descendant.name} ({descendant.sample_id})")
                    else:
                        st.write("No descendants.")
            except ValueError as e:
                st.error(f"Error retrieving lineage: {str(e)}")
            
            # Contained Samples
            st.subheader("Contained Samples")
            if sample.contained_sample_ids:
                contained_samples = service.get_contained_samples(sample_id)
                for contained in contained_samples:
                    st.write(f"- {contained.name} ({contained.sample_id})")
            else:
                st.write("No contained samples.")
            
            # Files
            st.subheader("Associated Files")
            if sample.file_paths:
                for file_path in sample.file_paths:
                    st.write(f"- {file_path}")
            else:
                st.write("No files associated with this sample.")
        else:
            st.error(f"Sample with ID {sample_id} not found.")

# Footer
st.sidebar.divider()
st.sidebar.caption("BLIMS v0.1.0")