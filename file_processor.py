import base64
import os
from typing import List, Tuple, Dict, Any

def process_uploaded_files(uploaded_files: List[Any]) -> Tuple[List[str], List[str], List[str], List[str]]:
    """
    Process uploaded files and return lists of encoded data, document types, media type prefixes, and file extensions.
    
    Args:
        uploaded_files: List of uploaded file objects from Streamlit
        
    Returns:
        Tuple containing:
        - List of base64 encoded data
        - List of document types
        - List of media type prefixes
        - List of file extensions
    """
    encoded_data_list = []
    doc_types = []
    media_type_prefixes = []
    file_extension_list = []
    
    for uploaded_file in uploaded_files:
        encoded_data = base64.standard_b64encode(uploaded_file.getvalue()).decode("utf-8")
        file_extension = os.path.splitext(uploaded_file.name)[1]
        
        if file_extension == ".pdf":
            doc_type = "document"
            media_type_prefix = "application"
        elif file_extension in [".jpeg", ".png", ".webp"]:
            doc_type = "image"
            media_type_prefix = "image"
        
        file_extension_list.append(file_extension)
        encoded_data_list.append(encoded_data)
        doc_types.append(doc_type)
        media_type_prefixes.append(media_type_prefix)
    
    return encoded_data_list, doc_types, media_type_prefixes, file_extension_list

def prepare_content_for_hm(user_query: str, uploaded_files: List[Any]) -> List[Dict[str, Any]]:
    """
    Prepare content for the human message including both text and files.
    
    Args:
        user_query: The text query from the user
        uploaded_files: List of uploaded file objects
        
    Returns:
        List of dictionaries containing the prepared content
    """
    if not uploaded_files:
        return user_query
        
    encoded_data_list, doc_types, media_type_prefixes, file_extension_list = process_uploaded_files(uploaded_files)
    content_for_hm = []

    for i, _ in enumerate(uploaded_files):
        file_input = {
            "type": doc_types[i],
            "source": {
                "type": "base64",
                "media_type": media_type_prefixes[i] + "/" + file_extension_list[i][1:],
                "data": encoded_data_list[i]
            }
        }
        content_for_hm.append(file_input)
    
    user_input = {
        "type": "text",
        "text": user_query if user_query else " "
    }
    content_for_hm.append(user_input)
    
    return content_for_hm 