import time
from abc import ABC, abstractmethod
from typing import Dict, Any

class BasePDFProcessor(ABC):
    """
    Abstract base class for all PDF library processors.
    This class enforces a uniform interface and defines the standard return schema
    so that results from different libraries can be easily formatted and compared.
    """
    
    def __init__(self, library_name: str):
        self.library_name = library_name

    @abstractmethod
    def extract_data(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extracts metrics, text, and structure from a PDF file.
        This must be implemented by each library-specific processor.
        
        Args:
            pdf_path (str): The absolute or relative path to the PDF file.
            
        Returns:
            Dict[str, Any]: A dictionary populated with the raw extracted data.
        """
        pass

    def process(self, pdf_path: str) -> Dict[str, Any]:
        """
        Orchestrates the extraction process. Wraps the extraction in a timer
        to capture the exact execution duration and provides fallback values
        for any missing keys, ensuring robustness.
        
        Args:
            pdf_path (str): The path to the PDF file.
            
        Returns:
            Dict[str, Any]: Standardized result dictionary.
        """
        start_time = time.perf_counter()
        
        # Initialize default return schema in case the extraction fails or is incomplete
        result = {
            "library_name": self.library_name,
            "processing_time": 0.0,
            "page_count": 0,
            "metadata": {
                "title": "Unknown",
                "author": "Unknown",
                "producer": "Unknown",
                "creation_date": "Unknown"
            },
            "extracted_text": "",
            "block_count": -1,       # -1 indicates "Unsupported/Not extracted" by this library
            "word_count": -1,        # -1 indicates "Unsupported/Not extracted" by this library
            "image_count": -1,       # -1 indicates "Unsupported/Not extracted" by this library
            "table_count": -1,       # -1 indicates "Unsupported/Not extracted" by this library
            "fonts": [],
            "dimensions": [],        # List of tuples: (width, height) for each page
            "charts_figures_detected": False,
            "pages_text": [],
            "pages_data": [],
            "warnings": []
        }
        
        try:
            # Call library-specific extraction logic
            extracted = self.extract_data(pdf_path)
            
            # Merge extracted data into the default result schema
            if isinstance(extracted, dict):
                for key, val in extracted.items():
                    if key == "metadata" and isinstance(val, dict):
                        # Merge metadata fields carefully to maintain structure
                        for meta_key in result["metadata"]:
                            result["metadata"][meta_key] = val.get(meta_key, "Unknown") or "Unknown"
                    else:
                        result[key] = val
                        
        except Exception as e:
            # Catch exceptions gracefully so that one library failing doesn't crash the entire run
            result["warnings"].append(f"Processing failed: {str(e)}")
            
        end_time = time.perf_counter()
        result["processing_time"] = end_time - start_time
        
        # Clean up any potential None values in metadata
        for k, v in result["metadata"].items():
            if v is None:
                result["metadata"][k] = "Unknown"
                
        return result
