"""
General utility functions for the DocBrain application.
"""
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

def sanitize_text(text: str) -> str:
    """
    Sanitize text by removing excessive whitespace and normalizing line breaks.
    
    Args:
        text: The text to sanitize
        
    Returns:
        The sanitized text
    """
    if not text:
        return ""
    
    # Replace multiple spaces with a single space
    text = " ".join(text.split())
    
    # Replace multiple newlines with a single newline
    lines = text.splitlines()
    non_empty_lines = [line.strip() for line in lines if line.strip()]
    return "\n".join(non_empty_lines)

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of a specified size.
    
    Args:
        lst: The list to split
        chunk_size: The size of each chunk
        
    Returns:
        A list of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two dictionaries, with values from dict2 taking precedence.
    
    Args:
        dict1: The first dictionary
        dict2: The second dictionary
        
    Returns:
        The merged dictionary
    """
    result = dict1.copy()
    result.update(dict2)
    return result
