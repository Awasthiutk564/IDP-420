import pypdf
from typing import Dict, Any
from .base_processor import BasePDFProcessor

class PyPDFProcessor(BasePDFProcessor):
    """
    PDF Processor implementation using pypdf.
    pypdf is a pure Python library designed to be lightweight and fast.
    It is great for simple text extraction, page splitting, merging, and basic metadata reading.
    It does not support complex layout analysis (such as tables or text blocks),
    and its text extraction can sometimes fail to preserve spacing/layout compared to advanced libraries.
    """
    
    def __init__(self):
        super().__init__(library_name="pypdf")

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
            "block_count": -1,       # pypdf does not support block-level layout analysis
            "word_count": 0,
            "image_count": 0,
            "table_count": -1,       # pypdf has no native table detection
            "fonts": [],
            "dimensions": [],
            "warnings": []
        }
        
        # Open the PDF file
        reader = pypdf.PdfReader(pdf_path)
        extracted["page_count"] = len(reader.pages)
        
        # Extract metadata
        meta = reader.metadata
        if meta:
            extracted["metadata"]["title"] = meta.title or "Unknown"
            extracted["metadata"]["author"] = meta.author or "Unknown"
            extracted["metadata"]["producer"] = meta.producer or "Unknown"
            extracted["metadata"]["creation_date"] = meta.creation_date or "Unknown"
            
        full_text_list = []
        unique_fonts = set()
        
        # Process page by page
        for page_num, page in enumerate(reader.pages):
            # Page dimensions
            try:
                # mediabox provides width and height
                mediabox = page.mediabox
                width = float(mediabox.width)
                height = float(mediabox.height)
                extracted["dimensions"].append((width, height))
            except Exception as e:
                extracted["dimensions"].append((0.0, 0.0))
                extracted["warnings"].append(f"Page {page_num + 1}: Failed to extract dimensions: {e}")
                
            # Text extraction
            try:
                text = page.extract_text()
                if text:
                    full_text_list.append(text)
                    # Estimate word count by splitting text
                    extracted["word_count"] += len(text.split())
            except Exception as e:
                extracted["warnings"].append(f"Page {page_num + 1}: Failed to extract text: {e}")
                
            # Image count
            try:
                images = page.images
                extracted["image_count"] += len(images)
            except Exception as e:
                extracted["warnings"].append(f"Page {page_num + 1}: Failed to extract images: {e}")
                
            # Fonts detection
            try:
                if "/Resources" in page and "/Font" in page["/Resources"]:
                    font_dict = page["/Resources"]["/Font"]
                    # If it's a reference or direct object, get the dictionary
                    font_dict_obj = font_dict.get_object()
                    for font_name in font_dict_obj:
                        font_info = font_dict_obj[font_name].get_object()
                        if "/BaseFont" in font_info:
                            base_font = font_info["/BaseFont"]
                            # Clean up the name (remove leading slash and subset prefixes)
                            font_str = str(base_font).replace("/", "")
                            if "+" in font_str:
                                font_str = font_str.split("+")[1]
                            unique_fonts.add(font_str)
            except Exception as e:
                # Keep font extraction failure silent or log as warning
                extracted["warnings"].append(f"Page {page_num + 1}: Font extraction failed: {e}")
                
        extracted["extracted_text"] = "\n".join(full_text_list)
        extracted["fonts"] = sorted(list(unique_fonts))
        extracted["warnings"].append("Block layout extraction and table detection are unsupported by pypdf")
        
        return extracted
