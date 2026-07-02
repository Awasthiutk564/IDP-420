import os
from typing import Dict, Any
from .base_processor import BasePDFProcessor

# pdfminer.six imports for page-by-page parsing
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTChar, LTFigure, LTImage
from pdfminer.pdftypes import resolve1

class PDFMinerProcessor(BasePDFProcessor):
    """
    PDF Processor implementation using pdfminer.six.
    pdfminer.six is a pure Python library focused on layout analysis.
    It reconstructs the page layout recursively, allowing us to find text blocks,
    individual characters (with their fonts), and images.
    It is precise but generally slower than PyMuPDF because it is written in pure Python.
    """
    
    def __init__(self):
        super().__init__(library_name="pdfminer.six")

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
            "table_count": -1,       # pdfminer has no native table detection
            "fonts": [],
            "dimensions": [],
            "warnings": []
        }
        
        if not os.path.exists(pdf_path):
            extracted["warnings"].append("File not found.")
            return extracted

        with open(pdf_path, 'rb') as fp:
            # 1. Parse Metadata using PDFParser and PDFDocument
            parser = PDFParser(fp)
            try:
                doc = PDFDocument(parser)
                if doc.info:
                    meta_dict = {}
                    for info in doc.info:
                        for k, v in info.items():
                            resolved = resolve1(v)
                            # Decode byte strings, handling UTF-16 BOM and other encodings
                            if isinstance(resolved, bytes):
                                if resolved.startswith(b'\xfe\xff'):
                                    try:
                                        decoded = resolved.decode('utf-16', errors='ignore')
                                    except Exception:
                                        decoded = resolved.decode('latin1', errors='ignore')
                                else:
                                    try:
                                        decoded = resolved.decode('utf-8', errors='ignore')
                                    except Exception:
                                        decoded = resolved.decode('latin1', errors='ignore')
                            else:
                                decoded = str(resolved)
                            meta_dict[k.lower()] = decoded
                    
                    extracted["metadata"]["title"] = meta_dict.get("title", "Unknown") or "Unknown"
                    extracted["metadata"]["author"] = meta_dict.get("author", "Unknown") or "Unknown"
                    extracted["metadata"]["producer"] = meta_dict.get("producer", "Unknown") or "Unknown"
                    extracted["metadata"]["creation_date"] = meta_dict.get("creationdate", "Unknown") or "Unknown"
            except Exception as e:
                extracted["warnings"].append(f"Failed to parse metadata: {e}")
            
            # Reset file pointer and re-initialize layout parser
            fp.seek(0)
            
            rsrcmgr = PDFResourceManager()
            laparams = LAParams()
            device = PDFPageAggregator(rsrcmgr, laparams=laparams)
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            
            pages = list(PDFPage.get_pages(fp))
            extracted["page_count"] = len(pages)
            
            full_text_list = []
            unique_fonts = set()
            
            def count_images_recursive(element) -> int:
                """Recursively count LTImage elements inside LTFigure/containers."""
                count = 0
                if isinstance(element, LTImage):
                    count += 1
                elif isinstance(element, LTFigure):
                    for child in element:
                        count += count_images_recursive(child)
                return count

            # 2. Iterate through each page for detailed layout processing
            for page_num, page in enumerate(pages):
                # Extract page dimensions: page.mediabox is (x0, y0, x1, y1)
                # width = x1 - x0, height = y1 - y0
                try:
                    x0, y0, x1, y1 = page.mediabox
                    width = x1 - x0
                    height = y1 - y0
                    extracted["dimensions"].append((width, height))
                except Exception as e:
                    extracted["dimensions"].append((0.0, 0.0))
                    extracted["warnings"].append(f"Page {page_num + 1}: Failed to extract dimensions: {e}")
                
                # Process layout
                try:
                    interpreter.process_page(page)
                    layout = device.get_result()
                    
                    page_text_blocks = []
                    
                    for element in layout:
                        # Count text blocks (LTTextBox represents a block of lines)
                        if isinstance(element, LTTextBox):
                            extracted["block_count"] += 1
                            text_content = element.get_text()
                            page_text_blocks.append(text_content)
                            
                            # Estimate word count by splitting
                            words = text_content.split()
                            extracted["word_count"] += len(words)
                            
                            # Extract fonts by traversing individual characters (LTChar)
                            for text_line in element:
                                # A textbox contains textlines
                                if hasattr(text_line, '__iter__'):
                                    for character in text_line:
                                        if isinstance(character, LTChar):
                                            if character.fontname:
                                                # Strip typical PDF subsets like 'ABCDEF+Arial'
                                                font_name = character.fontname
                                                if '+' in font_name:
                                                    font_name = font_name.split('+')[1]
                                                unique_fonts.add(font_name)
                                                
                        elif isinstance(element, (LTImage, LTFigure)):
                            extracted["image_count"] += count_images_recursive(element)
                            
                    full_text_list.append("".join(page_text_blocks))
                except Exception as e:
                    extracted["warnings"].append(f"Page {page_num + 1}: Processing layout failed: {e}")

            # Combine page texts
            extracted["extracted_text"] = "\n".join(full_text_list)
            extracted["fonts"] = sorted(list(unique_fonts))
            
            # Close layout device
            device.close()

        extracted["warnings"].append("Table extraction is unsupported by pdfminer.six")
        return extracted
