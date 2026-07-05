import pdfplumber
import re
import os
from collections import Counter
from typing import Dict, Any, List
from pdfminer.layout import LTTextBox
from .base_processor import BasePDFProcessor
from utils.hierarchy_builder import (
    Word, Line, Block, Section, Table, ImageObj, ChartObj, HyperlinkObj, PageObj, DocumentObj, HierarchyBuilder
)

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
            "charts_figures_detected": False,
            "pages_text": [],
            "pages_data": [],
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
                
            # Initialize DocumentObj
            filename = os.path.basename(pdf_path)
            doc_obj = DocumentObj(filename=filename, metadata=extracted["metadata"])
            
            full_text_list = []
            unique_fonts = set()
            
            # Process page by page
            for page_num, page in enumerate(pdf.pages):
                # Page dimensions
                width = float(page.width)
                height = float(page.height)
                extracted["dimensions"].append((width, height))
                
                # Text extraction
                text = page.extract_text() or ""
                full_text_list.append(text)
                
                # Initialize page object
                page_obj = PageObj(page_number=page_num + 1, width=width, height=height)
                
                # 1. Image extraction & classification
                try:
                    images = page.images
                    for img in images:
                        ibbox = (float(img["x0"]), float(img["top"]), float(img["x1"]), float(img["bottom"]))
                        w_img = float(img["width"])
                        h_img = float(img["height"])
                        
                        fig_type, fig_conf = HierarchyBuilder.classify_figure_type(ibbox, width, height, is_vector=False)
                        page_obj.images.append(ImageObj(
                            bbox=ibbox,
                            width=w_img,
                            height=h_img,
                            resolution="72x72 dpi",
                            figure_type=fig_type,
                            confidence=fig_conf
                        ))
                except Exception as e:
                    extracted["warnings"].append(f"Page {page_num + 1}: Failed to extract images: {e}")
                    
                # 2. Table extraction
                try:
                    tbls = page.find_tables()
                    if tbls:
                        for t in tbls:
                            tbbox = (float(t.bbox[0]), float(t.bbox[1]), float(t.bbox[2]), float(t.bbox[3]))
                            page_obj.tables.append(Table(
                                rows=len(t.rows),
                                columns=len(t.cols),
                                bbox=tbbox,
                                confidence=0.95
                            ))
                except Exception as e:
                    extracted["warnings"].append(f"Page {page_num + 1}: Table detection failed: {e}")
                    
                # 3. Fonts
                try:
                    chars = page.chars
                    for char in chars:
                        font_name = char.get("fontname")
                        if font_name:
                            if '+' in font_name:
                                font_name = font_name.split('+')[1]
                            unique_fonts.add(font_name)
                except Exception as e:
                    extracted["warnings"].append(f"Page {page_num + 1}: Font extraction failed: {e}")
                    
                # 4. Text layout parser (Words -> Lines)
                page_lines = []
                base_size = 10.0
                rotated_text_count = 0
                try:
                    chars = page.chars
                    sizes = []
                    for char in chars:
                        f_sz = char.get("size")
                        if f_sz:
                            sizes.append(round(f_sz, 1))
                    if sizes:
                        base_size = Counter(sizes).most_common(1)[0][0]
                        
                    # Group words extracted by pdfplumber into lines by matching vertical coordinates (top/bottom)
                    words_extracted = page.extract_words()
                    words_by_line = {}
                    for w in words_extracted:
                        top_val = round(float(w["top"]), 1)
                        found_key = None
                        for k in words_by_line:
                            if abs(k - top_val) < 3.0:
                                found_key = k
                                break
                        if found_key is None:
                            words_by_line[top_val] = [w]
                        else:
                            words_by_line[found_key].append(w)
                            
                    for top_key in sorted(words_by_line.keys()):
                        words_list = []
                        line_words = sorted(words_by_line[top_key], key=lambda w: float(w["x0"]))
                        for lw in line_words:
                            text_w = lw["text"]
                            if not text_w.strip():
                                continue
                            x0_w = float(lw["x0"])
                            top_w = float(lw["top"])
                            x1_w = float(lw["x1"])
                            bottom_w = float(lw["bottom"])
                            
                            f_name = "Unknown"
                            f_size = 10.0
                            f_style = "Regular"
                            f_color = "#000000"
                            
                            matching_chars = [c for c in chars if abs(float(c.get("x0", 0)) - x0_w) < 4.0 and abs(float(c.get("top", 0)) - top_w) < 4.0]
                            if matching_chars:
                                m_c = matching_chars[0]
                                f_name = m_c.get("fontname", "Unknown")
                                if "+" in f_name:
                                    f_name = f_name.split("+")[1]
                                f_size = round(m_c.get("size", 10.0), 1)
                                f_style = "Bold" if "bold" in f_name.lower() else ("Italic" if ("italic" in f_name.lower() or "oblique" in f_name.lower()) else "Regular")
                                color_val = m_c.get("non_stroking_color") or 0
                                f_color = f"#{color_val}" if isinstance(color_val, str) else (
                                    f"#{int(color_val[0]*255):02x}{int(color_val[1]*255):02x}{int(color_val[2]*255):02x}" 
                                    if isinstance(color_val, (list, tuple)) and len(color_val) >= 3 else "#000000"
                                )
                                
                            font_info = {
                                "fontname": f_name,
                                "size": f_size,
                                "style": f_style,
                                "color": f_color
                            }
                            if font_info not in page_obj.fonts:
                                page_obj.fonts.append(font_info)
                                
                            # Check rotation
                            if matching_chars and matching_chars[0].get("matrix") and matching_chars[0]["matrix"][1] != 0:
                                rotated_text_count += 1
                                
                            words_list.append(Word(
                                text=text_w,
                                bbox=(x0_w, top_w, x1_w, bottom_w),
                                font_name=f_name,
                                font_size=f_size,
                                font_style=f_style,
                                color=f_color
                            ))
                            
                        if words_list:
                            x0_l = min(w.bbox[0] for w in words_list)
                            top_l = min(w.bbox[1] for w in words_list)
                            x1_l = max(w.bbox[2] for w in words_list)
                            bottom_l = max(w.bbox[3] for w in words_list)
                            page_lines.append(Line(words=words_list, bbox=(x0_l, top_l, x1_l, bottom_l)))
                except Exception as e:
                    extracted["warnings"].append(f"Page {page_num + 1}: Layout parse failed: {e}")
                    
                # 5. Hyperlinks
                try:
                    if hasattr(page, "hyperlinks") and page.hyperlinks:
                        for link in page.hyperlinks:
                            lbbox = (float(link["x0"]), float(link["top"]), float(link["x1"]), float(link["bottom"]))
                            page_obj.hyperlinks.append(HyperlinkObj(url=link.get("uri", ""), bbox=lbbox))
                except Exception:
                    pass
                    
                # 6. Charts extraction
                try:
                    rects_c = page.rects
                    lines_c = page.lines
                    curves_c = page.curves
                    
                    if rects_c or lines_c or curves_c:
                        extracted["charts_figures_detected"] = True
                        chart_type = "Unknown Figure"
                        if len(rects_c) >= 4:
                            chart_type = "Bar Chart"
                        elif len(curves_c) >= 2 and len(rects_c) == 0:
                            chart_type = "Pie Chart"
                        elif len(lines_c) >= 3 and len(curves_c) == 0:
                            chart_type = "Line Chart"
                        elif len(rects_c) > 10 and len(lines_c) == 0:
                            chart_type = "Scatter Plot"
                            
                        x0s = [float(r["x0"]) for r in rects_c + lines_c + curves_c]
                        y0s = [float(r["top"]) for r in rects_c + lines_c + curves_c]
                        x1s = [float(r["x1"]) for r in rects_c + lines_c + curves_c]
                        y1s = [float(r["bottom"]) for r in rects_c + lines_c + curves_c]
                        
                        if x0s:
                            cbbox = (min(x0s), min(y0s), max(x1s), max(y1s))
                            fig_type, fig_conf = HierarchyBuilder.classify_figure_type(cbbox, width, height, is_vector=True, num_paths=len(rects_c)+len(lines_c)+len(curves_c))
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
            
            return extracted
