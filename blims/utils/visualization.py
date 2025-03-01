"""Visualization utilities for BLIMS."""

import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network
import tempfile
import os
from typing import List, Dict, Tuple, Any


def create_sample_network(samples: List[Any]) -> nx.DiGraph:
    """Create a network graph of samples and their relationships.
    
    Creates a directed graph where nodes are samples and edges represent
    relationships (parent-child, container-contained).
    
    Args:
        samples: List of Sample objects
        
    Returns:
        A NetworkX directed graph
    """
    G = nx.DiGraph()
    
    # Add all samples as nodes
    for sample in samples:
        is_container = getattr(sample, 'is_container', False)
        G.add_node(
            str(sample.id),
            id=str(sample.id),
            label=sample.name,
            title=f"{sample.name} ({sample.sample_type})",
            type=sample.sample_type,
            is_container=is_container,
        )
    
    # Add container edges
    for sample in samples:
        if hasattr(sample, 'container_id') and sample.container_id:
            container_id = str(sample.container_id)
            if G.has_node(container_id):
                G.add_edge(
                    container_id, 
                    str(sample.id),
                    relation="contains"
                )
    
    # Add parent-child edges
    for sample in samples:
        if hasattr(sample, 'parent_ids') and sample.parent_ids:
            for parent_id in sample.parent_ids:
                parent_id_str = str(parent_id)
                if G.has_node(parent_id_str):
                    G.add_edge(
                        parent_id_str, 
                        str(sample.id),
                        relation="parent_of"
                    )
    
    return G


def draw_network_matplotlib(G: nx.DiGraph) -> Tuple[plt.Figure, Dict]:
    """Draw a network graph using Matplotlib.
    
    Args:
        G: NetworkX graph to draw
        
    Returns:
        Tuple of (matplotlib figure, node positions)
    """
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Node colors based on type
    node_colors = []
    for node in G.nodes():
        if G.nodes[node].get('is_container', False):
            node_colors.append('skyblue')
        else:
            node_colors.append('lightgreen')
    
    # Edge colors based on relationship
    edge_colors = []
    for u, v, data in G.edges(data=True):
        if data.get('relation') == 'contains':
            edge_colors.append('blue')
        else:
            edge_colors.append('green')
    
    # Calculate position using spring layout
    pos = nx.spring_layout(G)
    
    # Draw the graph
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, alpha=0.8, node_size=500)
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=1.5, arrowsize=15)
    nx.draw_networkx_labels(G, pos, labels={node: G.nodes[node].get('label', node) for node in G.nodes()})
    
    # Remove axes
    ax.axis('off')
    
    return fig, pos


def draw_network_pyvis(G: nx.DiGraph) -> str:
    """Draw a network graph using Pyvis for interactive visualization.
    
    Args:
        G: NetworkX graph to draw
        
    Returns:
        HTML string of the rendered graph
    """
    # Create a Pyvis network
    net = Network(height="600px", width="100%", directed=True, notebook=False)
    
    # Add all nodes
    for node, attrs in G.nodes(data=True):
        net.add_node(
            node,
            label=attrs.get('label', node),
            title=attrs.get('title', node),
            color='skyblue' if attrs.get('is_container', False) else 'lightgreen'
        )
    
    # Add all edges
    for u, v, data in G.edges(data=True):
        relation = data.get('relation', '')
        color = 'blue' if relation == 'contains' else 'green'
        net.add_edge(u, v, title=relation, color=color)
    
    # Set physics options for better visualization
    net.set_options("""
    {
      "physics": {
        "stabilization": {
          "iterations": 100
        },
        "barnesHut": {
          "gravitationalConstant": -10000,
          "springLength": 150,
          "springConstant": 0.04
        }
      },
      "edges": {
        "arrows": {
          "to": {
            "enabled": true,
            "scaleFactor": 0.5
          }
        },
        "smooth": {
          "enabled": true,
          "type": "dynamic",
          "roundness": 0.5
        }
      }
    }
    """)
    
    # Create a temporary file to store the HTML
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as f:
        net.save_html(f.name)
        with open(f.name, 'r') as html_file:
            html_string = html_file.read()
        os.unlink(f.name)
    
    return html_string