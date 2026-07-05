import pypdf
import re
import os
from typing import Dict, Any, List
from .base_processor import BasePDFProcessor
from utils.hierarchy_builder import (
    Word, Line, Block, Section, Table, ImageObj, ChartObj, HyperlinkObj, PageObj, DocumentObj, HierarchyBuilder
)

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
            "charts_figures_detected": False,
            "pages_text": [],
            "pages_data": [],
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
        
        # Initialize DocumentObj
        filename = os.path.basename(pdf_path)
        doc_obj = DocumentObj(filename=filename, metadata=extracted["metadata"])
        
        full_text_list = []
        unique_fonts = set()
        
        # Process page by page
        for page_num, page in enumerate(reader.pages):
            try:
                mediabox = page.mediabox
                width = float(mediabox.width)
                height = float(mediabox.height)
                extracted["dimensions"].append((width, height))
            except Exception as e:
                width = 612.0
                height = 792.0
                extracted["dimensions"].append((0.0, 0.0))
                extracted["warnings"].append(f"Page {page_num + 1}: Failed to extract dimensions: {e}")
                
            # Text extraction
            text = ""
            try:
                text = page.extract_text() or ""
                if text:
                    full_text_list.append(text)
            except Exception as e:
                extracted["warnings"].append(f"Page {page_num + 1}: Failed to extract text: {e}")
                
            # Initialize page object
            page_obj = PageObj(page_number=page_num + 1, width=width, height=height)
            
            # Approximate Page lines & words from raw string split
            page_lines = []
            raw_lines = [rl.strip() for rl in text.splitlines() if rl.strip()]
            
            if raw_lines:
                num_lines = len(raw_lines)
                line_height_est = (height * 0.8) / max(num_lines, 1)
                curr_y = height * 0.1
                
                for r_line in raw_lines:
                    words_in_line = r_line.split()
                    words_list = []
                    if words_in_line:
                        num_w = len(words_in_line)
                        line_width_est = width * 0.8
                        w_width_est = line_width_est / max(num_w, 1)
                        curr_x = width * 0.1
                        
                        for rw in words_in_line:
                            w_bbox = (curr_x, curr_y, curr_x + w_width_est, curr_y + line_height_est)
                            words_list.append(Word(
                                text=rw,
                                bbox=w_bbox,
                                font_size=10.0
                            ))
                            curr_x += w_width_est + 2.0
                            
                        l_bbox = (width * 0.1, curr_y, width * 0.9, curr_y + line_height_est)
                        page_lines.append(Line(words=words_list, bbox=l_bbox))
                    curr_y += line_height_est
                    
            # 1. Images
            try:
                images = page.images
                for idx, img in enumerate(images):
                    ibbox = (50.0, 100.0 + idx*150.0, 250.0, 250.0 + idx*150.0)
                    fig_type, fig_conf = HierarchyBuilder.classify_figure_type(ibbox, width, height, is_vector=False)
                    page_obj.images.append(ImageObj(
                        bbox=ibbox,
                        width=200.0,
                        height=150.0,
                        resolution="72x72 dpi",
                        figure_type=fig_type,
                        confidence=fig_conf
                    ))
            except Exception as e:
                extracted["warnings"].append(f"Page {page_num + 1}: Failed to extract images: {e}")
                
            # 2. Fonts
            try:
                if "/Resources" in page and "/Font" in page["/Resources"]:
                    font_dict = page["/Resources"]["/Font"]
                    font_dict_obj = font_dict.get_object()
                    for font_name in font_dict_obj:
                        font_info_obj = font_dict_obj[font_name].get_object()
                        if "/BaseFont" in font_info_obj:
                            base_font = font_info_obj["/BaseFont"]
                            font_str = str(base_font).replace("/", "")
                            if "+" in font_str:
                                font_str = font_str.split("+")[1]
                            unique_fonts.add(font_str)
                            
                            style = "Regular"
                            if "bold" in font_str.lower():
                                style = "Bold"
                            elif "italic" in font_str.lower() or "oblique" in font_str.lower():
                                style = "Italic"
                                
                            page_obj.fonts.append({
                                "fontname": font_str,
                                "size": 10.0,
                                "style": style,
                                "color": "#000000"
                            })
            except Exception as e:
                extracted["warnings"].append(f"Page {page_num + 1}: Font extraction failed: {e}")
                
            # 3. Reading complexity & block classification
            cols, layout_label = HierarchyBuilder.detect_layout_columns(page_lines, width)
            page_obj.reading_complexity = layout_label
            
            sorted_lines = HierarchyBuilder.extract_reading_order(page_lines, cols, width)
            blocks = HierarchyBuilder.classify_headings_and_blocks(sorted_lines, 10.0, height)
            
            # Sections assignment (Header, Body, Footer)
            header_blocks = []
            body_blocks = []
            footer_blocks = []
            
            for b in blocks:
                bx0, by0, bx1, by1 = b.bbox
                if by1 <= height * 0.12:
                    header_blocks.append(b)
                elif by0 >= height * 0.88:
                    footer_blocks.append(b)
                else:
                    body_blocks.append(b)
                    
            if header_blocks:
                page_obj.sections.append(Section(section_type="header", bbox=(0, 0, width, height * 0.12), blocks=header_blocks))
            if body_blocks:
                page_obj.sections.append(Section(section_type="body", bbox=(0, height * 0.12, width, height * 0.88), blocks=body_blocks))
            if footer_blocks:
                page_obj.sections.append(Section(section_type="footer", bbox=(0, height * 0.88, width, height), blocks=footer_blocks))
                
            # Associate captions
            HierarchyBuilder.associate_captions(blocks, page_obj)
            
            # Counts
            char_cnt = len(text.strip())
            word_cnt = len(text.strip().split())
            page_obj.char_count = char_cnt
            page_obj.word_count = word_cnt
            
            if char_cnt == 0:
                if len(page_obj.images) > 0 or len(page_obj.charts) > 0:
                    page_obj.document_quality = "OCR required"
                    page_obj.ocr_recommended = True
                else:
                    page_obj.document_quality = "Scanned"
                    page_obj.ocr_recommended = True
            else:
                page_obj.document_quality = "Digitally generated"
                
            # Calculate page extraction confidence
            page_obj.confidence_score = sum(b.confidence for b in blocks) / len(blocks) if blocks else 0.5
            
            h1_l = [b.text for b in blocks if b.block_type == "heading_1"]
            h2_l = [b.text for b in blocks if b.block_type == "heading_2"]
            h3_l = [b.text for b in blocks if b.block_type == "heading_3"]
            paras_l = [b.text for b in blocks if b.block_type == "paragraph"]
            bullets_l = [b.text for b in blocks if b.block_type == "bullet_list_item"]
            numbered_l = [b.text for b in blocks if b.block_type == "numbered_list_item"]
            footnotes_l = [b.text for b in blocks if b.block_type == "footnote"]
            page_numbers_l = [b.text for b in blocks if b.block_type == "page_number"]
            
            page_data = {
                "page_number": page_num + 1,
                "headings": {"h1": h1_l, "h2": h2_l, "h3": h3_l},
                "paragraphs": paras_l,
                "bullet_lists": bullets_l,
                "numbered_lists": numbered_l,
                "tables": [t.to_dict() for t in page_obj.tables],
                "images": [i.to_dict() for i in page_obj.images],
                "charts": [c.to_dict() for c in page_obj.charts],
                "hyperlinks": [h.to_dict() for h in page_obj.hyperlinks],
                "footnotes": footnotes_l,
                "headers": page_obj.headers,
                "footers": page_obj.footers,
                "page_numbers": page_numbers_l,
                "fonts": page_obj.fonts,
                "word_count": word_cnt,
                "char_count": char_cnt,
                "rotated_text_count": 0,
                "reading_order_quality": "High",
                "columns_detected": cols,
                "reading_complexity": layout_label,
                "document_quality": page_obj.document_quality,
                "ocr_recommended": page_obj.ocr_recommended,
                "bounding_boxes": [{"category": b.block_type, "bbox": b.bbox} for b in blocks]
            }
            extracted["pages_data"].append(page_data)
            doc_obj.pages.append(page_obj)
            
        # Cross page runner headers footers
        HierarchyBuilder.process_header_footers_cross_pages(doc_obj.pages)
        for idx, p in enumerate(doc_obj.pages):
            extracted["pages_data"][idx]["headers"] = p.headers
            extracted["pages_data"][idx]["footers"] = p.footers
            extracted["pages_data"][idx]["page_numbers"] = p.page_numbers
            
        doc_obj.page_count = len(doc_obj.pages)
        extracted["hierarchy"] = doc_obj.to_dict()
        extracted["image_count"] = sum(len(p.images) for p in doc_obj.pages)
        extracted["table_count"] = sum(len(p.tables) for p in doc_obj.pages)
        extracted["extracted_text"] = "\n".join(full_text_list)
        extracted["pages_text"] = full_text_list
        extracted["fonts"] = sorted(list(unique_fonts))
        extracted["warnings"].append("Block layout extraction and table detection are unsupported by pypdf")
        
        return extracted
