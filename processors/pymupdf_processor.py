import fitz  # PyMuPDF
from typing import Dict, Any
from .base_processor import BasePDFProcessor

class PyMuPDFProcessor(BasePDFProcessor):
    """
    PDF Processor implementation using PyMuPDF (fitz).
    PyMuPDF is a highly performant C-based wrapper around MuPDF.
    It is extremely fast and has rich support for text, blocks, layout, fonts, images, and tables.
    """
    
    def __init__(self):
        super().__init__(library_name="PyMuPDF (fitz)")

    def extract_data(self, pdf_path: str) -> Dict[str, Any]:
        extracted = {
            "page_count": 0,
            "metadata": {
                "title": "Unknown",
                "author": "Unknown",
                "producer": "Unknown",
                "creation_date": "Unknown"
            },
            "extracted_text": "",
            "block_count": 0,
            "word_count": 0,
            "image_count": 0,
            "table_count": 0,
            "fonts": [],
            "dimensions": [],
            "warnings": []
        }
        
        # Open the document
        doc = fitz.open(pdf_path)
        extracted["page_count"] = len(doc)
        
        # Extract metadata
        meta = doc.metadata
        if meta:
            extracted["metadata"]["title"] = meta.get("title", "Unknown") or "Unknown"
            extracted["metadata"]["author"] = meta.get("author", "Unknown") or "Unknown"
            extracted["metadata"]["producer"] = meta.get("producer", "Unknown") or "Unknown"
            extracted["metadata"]["creation_date"] = meta.get("creationDate", "Unknown") or "Unknown"
            
        full_text_list = []
        unique_fonts = set()
        
        # Process page by page
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Dimensions: PyMuPDF rect gives width and height
            width = page.rect.width
            height = page.rect.height
            extracted["dimensions"].append((width, height))
            
            # Text extraction
            page_text = page.get_text("text")
            full_text_list.append(page_text)
            
            # Blocks count: get_text("blocks") returns a list of block tuples
            # Tuple structure: (x0, y0, x1, y1, "block text", block_no, block_type)
            # block_type 0 is text, block_type 1 is image
            blocks = page.get_text("blocks")
            extracted["block_count"] += len(blocks)
            
            # Word count: get_text("words") returns lists of word tuples
            # Tuple structure: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
            words = page.get_text("words")
            extracted["word_count"] += len(words)
            
            # Image count: get_images returns tuples representing images embedded in the page
            try:
                images = page.get_images(full=True)
                extracted["image_count"] += len(images)
            except Exception as e:
                extracted["warnings"].append(f"Page {page_num + 1}: Failed to count images: {e}")
            
            # Table count: PyMuPDF (since v1.21.0) supports table detection
            try:
                tables = page.find_tables()
                extracted["table_count"] += len(tables.tables) if tables else 0
            except Exception as e:
                extracted["table_count"] = -1  # Mark as unsupported/error if table detection fails
                extracted["warnings"].append(f"Page {page_num + 1}: Table extraction failed or unsupported: {e}")
                
            # Fonts detection: get_fonts() returns metadata list of fonts
            # Structure: [(xref, ext, type, basefont, name, encoding), ...]
            try:
                fonts = page.get_fonts()
                for f in fonts:
                    # font name is typically at index 3
                    if len(f) > 3:
                        unique_fonts.add(f[3])
            except Exception as e:
                extracted["warnings"].append(f"Page {page_num + 1}: Failed to get fonts: {e}")
                
        # Combine text from all pages
        extracted["extracted_text"] = "\n".join(full_text_list)
        extracted["fonts"] = sorted(list(unique_fonts))
        
        doc.close()
        return extracted
