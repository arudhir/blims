"""File utilities for handling and validating files."""

import hashlib
import os
from typing import Any, Dict, Optional, Tuple


def validate_file_exists(file_path: str) -> bool:
    """Check if a file exists.

    Args:
        file_path: Path to the file

    Returns:
        True if the file exists, False otherwise
    """
    return os.path.isfile(file_path)


def calculate_file_hash(file_path: str, algorithm: str = "sha256") -> Optional[str]:
    """Calculate the hash of a file.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use (default: SHA-256)

    Returns:
        File hash string or None if file not found
    """
    if not validate_file_exists(file_path):
        return None

    hash_obj = hashlib.new(algorithm)

    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()


def get_file_metadata(file_path: str) -> Dict[str, Any]:
    """Get metadata for a file.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with file metadata
    """
    if not validate_file_exists(file_path):
        return {"exists": False}

    stats = os.stat(file_path)

    return {
        "exists": True,
        "size_bytes": stats.st_size,
        "created_at": stats.st_ctime,
        "modified_at": stats.st_mtime,
        "file_name": os.path.basename(file_path),
        "extension": os.path.splitext(file_path)[1],
    }


def safe_file_path(base_dir: str, file_path: str) -> Tuple[bool, str]:
    """Create a safe absolute file path within a specific directory.

    This prevents path traversal attacks by ensuring the final path
    is within the specified base directory.

    Args:
        base_dir: The base directory that should contain the file
        file_path: The file path (can be relative or absolute)

    Returns:
        Tuple of (is_safe, absolute_path)
    """
    # Ensure base_dir is absolute
    base_dir = os.path.abspath(base_dir)

    # Join and normalize the path
    full_path = os.path.normpath(os.path.join(base_dir, file_path))

    # Check if the path is within the base directory
    is_safe = full_path.startswith(base_dir)

    return is_safe, full_path
