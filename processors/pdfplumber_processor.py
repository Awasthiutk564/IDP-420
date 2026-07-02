import pdfplumber
from typing import Dict, Any
from pdfminer.layout import LTTextBox
from .base_processor import BasePDFProcessor

class PDFPlumberProcessor(BasePDFProcessor):
    """
    PDF Processor implementation using pdfplumber.
    pdfplumber is built on top of pdfminer.six but provides a much cleaner,
    more developer-friendly API. It is exceptionally good at extracting tables,
    geometric shapes, and individual character/word bounding boxes.
    Like pdfminer, it is pure Python and can be slower for large documents.
    """
    
    def __init__(self):
        super().__init__(library_name="pdfplumber")

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
        
        # Open document
        with pdfplumber.open(pdf_path) as pdf:
            extracted["page_count"] = len(pdf.pages)
            
            # Extract metadata (standard dict)
            meta = pdf.metadata
            if meta:
                extracted["metadata"]["title"] = meta.get("Title", "Unknown") or "Unknown"
                extracted["metadata"]["author"] = meta.get("Author", "Unknown") or "Unknown"
                extracted["metadata"]["producer"] = meta.get("Producer", "Unknown") or "Unknown"
                extracted["metadata"]["creation_date"] = meta.get("CreationDate", "Unknown") or "Unknown"
                
            full_text_list = []
            unique_fonts = set()
            
            # Process page by page
            for page_num, page in enumerate(pdf.pages):
                # Page dimensions
                width = float(page.width)
                height = float(page.height)
                extracted["dimensions"].append((width, height))
                
                # Text extraction
                text = page.extract_text()
                if text:
                    full_text_list.append(text)
                
                # Word count: pdfplumber has extract_words() returning detailed bounding box info
                words = page.extract_words()
                extracted["word_count"] += len(words)
                
                # Block count: since pdfplumber is built on pdfminer, we can access page.layout (LTPage)
                try:
                    layout = page.layout
                    for element in layout:
                        if isinstance(element, LTTextBox):
                            extracted["block_count"] += 1
                except Exception as e:
                    # Fallback if page.layout is not populated
                    extracted["block_count"] = -1
                    extracted["warnings"].append(f"Page {page_num + 1}: Failed to access layout for block count: {e}")
                
                # Images: pdfplumber keeps list of image dictionaries in page.images
                try:
                    images = page.images
                    extracted["image_count"] += len(images)
                except Exception as e:
                    extracted["warnings"].append(f"Page {page_num + 1}: Failed to extract images: {e}")
                
                # Tables: pdfplumber has built-in table extraction algorithms
                try:
                    tables = page.find_tables()
                    extracted["table_count"] += len(tables) if tables else 0
                except Exception as e:
                    extracted["warnings"].append(f"Page {page_num + 1}: Table detection failed: {e}")
                    
                # Fonts: pdfplumber keeps details of every character in page.chars
                try:
                    chars = page.chars
                    for char in chars:
                        font_name = char.get("fontname")
                        if font_name:
                            # Strip subset prefix if present (e.g. "ABCDEF+Arial")
                            if '+' in font_name:
                                font_name = font_name.split('+')[1]
                            unique_fonts.add(font_name)
                except Exception as e:
                    extracted["warnings"].append(f"Page {page_num + 1}: Font extraction failed: {e}")
                    
            extracted["extracted_text"] = "\n".join(full_text_list)
            extracted["fonts"] = sorted(list(unique_fonts))
            
        return extracted
