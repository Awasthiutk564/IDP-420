import fitz  # PyMuPDF
import re
import os
from collections import Counter
from typing import Dict, Any, List
from .base_processor import BasePDFProcessor
from utils.hierarchy_builder import (
    Word, Line, Block, Section, Table, ImageObj, ChartObj, HyperlinkObj, PageObj, DocumentObj, HierarchyBuilder
)

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
            "charts_figures_detected": False,
            "pages_text": [],
            "pages_data": [],
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
            
        # Initialize DocumentObj
        filename = os.path.basename(pdf_path)
        doc_obj = DocumentObj(filename=filename, metadata=extracted["metadata"])
        
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
            
            # Initialize page object
            page_obj = PageObj(page_number=page_num + 1, width=width, height=height)
            
            # 1. Image extraction & classification
            try:
                images = page.get_images(full=True)
                img_infos = page.get_image_info(hashes=False)
                for img in img_infos:
                    ibbox = img.get("bbox", (0, 0, 0, 0))
                    width_i = img.get("width", 0)
                    height_i = img.get("height", 0)
                    xres = img.get("xres", 72)
                    yres = img.get("yres", 72)
                    
                    fig_type, fig_conf = HierarchyBuilder.classify_figure_type(ibbox, width, height, is_vector=False)
                    page_obj.images.append(ImageObj(
                        bbox=ibbox,
                        width=width_i,
                        height=height_i,
                        resolution=f"{xres}x{yres} dpi",
                        figure_type=fig_type,
                        confidence=fig_conf
                    ))
            except Exception as e:
                extracted["warnings"].append(f"Page {page_num + 1}: Failed to count images: {e}")
                
            # 2. Table extraction
            try:
                tbls = page.find_tables()
                if tbls:
                    for t in tbls.tables:
                        tbbox = (t.bbox[0], t.bbox[1], t.bbox[2], t.bbox[3])
                        page_obj.tables.append(Table(
                            rows=len(t.rows),
                            columns=len(t.cols),
                            bbox=tbbox,
                            confidence=0.95
                        ))
            except Exception as e:
                extracted["warnings"].append(f"Page {page_num + 1}: Table extraction failed: {e}")
                
            # 3. Fonts
            try:
                fonts = page.get_fonts()
                for f in fonts:
                    if len(f) > 3:
                        unique_fonts.add(f[3])
            except Exception as e:
                extracted["warnings"].append(f"Page {page_num + 1}: Failed to get fonts: {e}")
                
            # 4. Text layout parser (Spans -> Words -> Lines)
            page_lines = []
            base_size = 10.0
            rotated_text_count = 0
            try:
                page_dict = page.get_text("dict")
                sizes = []
                # Gather font sizes
                for b in page_dict.get("blocks", []):
                    if b.get("type") == 0:
                        for line in b.get("lines", []):
                            for span in line.get("spans", []):
                                sizes.append(round(span.get("size", 10), 1))
                if sizes:
                    base_size = Counter(sizes).most_common(1)[0][0]
                    
                for b in page_dict.get("blocks", []):
                    if b.get("type") == 0:
                        for line in b.get("lines", []):
                            words_list = []
                            # Line direction / rotated text
                            ldir = line.get("dir", (1.0, 0.0))
                            is_rotated = abs(ldir[0]) < 0.9
                            if is_rotated:
                                rotated_text_count += 1
                            
                            for span in line.get("spans", []):
                                span_text = span.get("text", "")
                                if not span_text.strip():
                                    continue
                                    
                                font_name = span.get("font", "Unknown")
                                if "+" in font_name:
                                    font_name = font_name.split("+")[1]
                                font_size = round(span.get("size", 10), 1)
                                font_style = "Bold" if (span.get("flags", 0) & 16) else ("Italic" if (span.get("flags", 0) & 2) else "Regular")
                                color_hex = f"#{span.get('color', 0):06x}"
                                
                                # Add font details to page fonts list
                                font_info = {
                                    "fontname": font_name,
                                    "size": font_size,
                                    "style": font_style,
                                    "color": color_hex
                                }
                                if font_info not in page_obj.fonts:
                                    page_obj.fonts.append(font_info)
                                    
                                # Split span text into words
                                span_bbox = span.get("bbox", (0, 0, 0, 0))
                                span_words = span_text.split()
                                if not span_words:
                                    continue
                                    
                                if len(span_words) == 1:
                                    words_list.append(Word(
                                        text=span_words[0],
                                        bbox=span_bbox,
                                        font_name=font_name,
                                        font_size=font_size,
                                        font_style=font_style,
                                        color=color_hex
                                    ))
                                else:
                                    # Interpolate coordinates
                                    x0, y0, x1, y1 = span_bbox
                                    span_w = x1 - x0
                                    total_chars = len(span_text)
                                    curr_x = x0
                                    for sw in span_words:
                                        sw_w = (len(sw) / total_chars) * span_w
                                        words_list.append(Word(
                                            text=sw,
                                            bbox=(curr_x, y0, curr_x + sw_w, y1),
                                            font_name=font_name,
                                            font_size=font_size,
                                            font_style=font_style,
                                            color=color_hex
                                        ))
                                        curr_x += sw_w + (1.0 / total_chars) * span_w
                                        
                            if words_list:
                                lbbox = line.get("bbox", (0, 0, 0, 0))
                                page_lines.append(Line(words=words_list, bbox=lbbox))
            except Exception as e:
                extracted["warnings"].append(f"Page {page_num + 1}: Layout dict parsing failed: {e}")
                
            # 5. Hyperlinks
            try:
                links = page.get_links()
                for link in links:
                    if link.get("kind") == fitz.LINK_URI:
                        uri = link.get("uri", "")
                        lfrom = link.get("from")
                        if lfrom:
                            page_obj.hyperlinks.append(HyperlinkObj(url=uri, bbox=(lfrom.x0, lfrom.y0, lfrom.x1, lfrom.y1)))
            except Exception as e:
                extracted["warnings"].append(f"Page {page_num + 1}: Hyperlink parsing failed: {e}")
                
            # 6. Charts extraction
            try:
                drawings = page.get_drawings()
                if drawings:
                    extracted["charts_figures_detected"] = True
                    rects_d = [d for d in drawings if d.get("type") == "re"]
                    lines_d = [d for d in drawings if d.get("type") == "l"]
                    curves_d = [d for d in drawings if d.get("type") == "c"]
                    
                    chart_type = "Unknown Figure"
                    if len(rects_d) >= 4:
                        chart_type = "Bar Chart"
                    elif len(curves_d) >= 2 and len(rects_d) == 0:
                        chart_type = "Pie Chart"
                    elif len(lines_d) >= 3 and len(curves_d) == 0:
                        chart_type = "Line Chart"
                    elif len(rects_d) > 10 and len(lines_d) == 0:
                        chart_type = "Scatter Plot"
                        
                    x0s = [d.get("rect").x0 for d in drawings if d.get("rect")]
                    y0s = [d.get("rect").y0 for d in drawings if d.get("rect")]
                    x1s = [d.get("rect").x1 for d in drawings if d.get("rect")]
                    y1s = [d.get("rect").y1 for d in drawings if d.get("rect")]
                    
                    if x0s:
                        cbbox = (min(x0s), min(y0s), max(x1s), max(y1s))
                        fig_type, fig_conf = HierarchyBuilder.classify_figure_type(cbbox, width, height, is_vector=True, num_paths=len(drawings))
                        page_obj.charts.append(ChartObj(
                            chart_type=chart_type,
                            bbox=cbbox,
                            figure_type=fig_type,
                            confidence=fig_conf
                        ))
            except Exception:
                pass
                
            # 7. Document layout and reading complexity classification
            cols, layout_label = HierarchyBuilder.detect_layout_columns(page_lines, width)
            page_obj.reading_complexity = layout_label
            
            # Sort lines using columns aware reading order
            sorted_lines = HierarchyBuilder.extract_reading_order(page_lines, cols, width)
            
            # Group lines into paragraphs, headings, footnotes
            blocks = HierarchyBuilder.classify_headings_and_blocks(sorted_lines, base_size, height)
            
            # 8. Sections assignment (Header, Body, Footer)
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
                
            # 9. Associate captions
            HierarchyBuilder.associate_captions(blocks, page_obj)
            
            # 10. Counts and OCR Recommended checks
            char_cnt = len(page_text.strip())
            word_cnt = len(page_text.strip().split())
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
            page_obj.confidence_score = sum(b.confidence for b in blocks) / len(blocks) if blocks else 1.0
            
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
                "rotated_text_count": rotated_text_count,
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
        # Update backwards compatible lists
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
        
        doc.close()
        return extracted
