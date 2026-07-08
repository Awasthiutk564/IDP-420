import os
import re
from collections import Counter
from typing import Dict, Any, List
from .base_processor import BasePDFProcessor
from utils.hierarchy_builder import (
    Word, Line, Block, Section, Table, ImageObj, ChartObj, HyperlinkObj, PageObj, DocumentObj, HierarchyBuilder
)

# pdfminer.six imports for page-by-page parsing
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox, LTChar, LTFigure, LTImage, LTCurve, LTLine, LTRect
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
            "charts_figures_detected": False,
            "pages_text": [],
            "pages_data": [],
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

            # Initialize DocumentObj
            filename = os.path.basename(pdf_path)
            doc_obj = DocumentObj(filename=filename, metadata=extracted["metadata"])
            
            full_text_list = []
            unique_fonts = set()
            
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
                    width = 612.0
                    height = 792.0
                    extracted["dimensions"].append((0.0, 0.0))
                    extracted["warnings"].append(f"Page {page_num + 1}: Failed to extract dimensions: {e}")
                
                # Process layout
                try:
                    interpreter.process_page(page)
                    layout = device.get_result()
                    
                    page_obj = PageObj(page_number=page_num + 1, width=width, height=height)
                    page_text_blocks = []
                    page_lines = []
                    
                    # Gather fonts and sizes first
                    sizes = []
                    for element in layout:
                        if isinstance(element, LTTextBox):
                            for line in element:
                                if hasattr(line, '__iter__'):
                                    for character in line:
                                        if isinstance(character, LTChar):
                                            if character.size:
                                                sizes.append(round(character.size, 1))
                    base_size = Counter(sizes).most_common(1)[0][0] if sizes else 10.0
                    
                    # Layout parser
                    for element in layout:
                        if isinstance(element, LTTextBox):
                            text_content = element.get_text().strip()
                            if not text_content:
                                continue
                            page_text_blocks.append(text_content)
                            
                            # Parse lines and words
                            for text_line in element:
                                if hasattr(text_line, '__iter__'):
                                    words_list = []
                                    # Collect characters of the line
                                    chars_in_line = []
                                    for character in text_line:
                                        if isinstance(character, LTChar):
                                            chars_in_line.append(character)
                                            
                                    # Group characters into words by checking spacing
                                    if chars_in_line:
                                        curr_word_chars = []
                                        for idx_c, char in enumerate(chars_in_line):
                                            curr_word_chars.append(char)
                                            # If space or large gap, commit word
                                            is_space = char.get_text() == ' '
                                            is_last = idx_c == len(chars_in_line) - 1
                                            is_gap = False
                                            if not is_last:
                                                next_char = chars_in_line[idx_c + 1]
                                                if next_char.x0 - char.x1 > 3.0:
                                                    is_gap = True
                                                    
                                            if is_space or is_gap or is_last:
                                                w_text = "".join(c.get_text() for c in curr_word_chars).strip()
                                                if w_text:
                                                    w_x0 = min(c.x0 for c in curr_word_chars)
                                                    w_y0 = min(height - c.y1 for c in curr_word_chars)
                                                    w_x1 = max(c.x1 for c in curr_word_chars)
                                                    w_y1 = max(height - c.y0 for c in curr_word_chars)
                                                    
                                                    f_char = curr_word_chars[0]
                                                    f_name = f_char.fontname or "Unknown"
                                                    if "+" in f_name:
                                                        f_name = f_name.split("+")[1]
                                                    unique_fonts.add(f_name)
                                                    f_size = round(f_char.size or 10.0, 1)
                                                    f_style = "Bold" if "bold" in f_name.lower() else ("Italic" if ("italic" in f_name.lower() or "oblique" in f_name.lower()) else "Regular")
                                                    
                                                    font_info = {
                                                        "fontname": f_name,
                                                        "size": f_size,
                                                        "style": f_style,
                                                        "color": "#000000"
                                                    }
                                                    if font_info not in page_obj.fonts:
                                                        page_obj.fonts.append(font_info)
                                                        
                                                    words_list.append(Word(
                                                        text=w_text,
                                                        bbox=(w_x0, w_y0, w_x1, w_y1),
                                                        font_name=f_name,
                                                        font_size=f_size,
                                                        font_style=f_style
                                                    ))
                                                curr_word_chars = []
                                                
                                        if words_list:
                                            lx0 = min(w.bbox[0] for w in words_list)
                                            ly0 = min(w.bbox[1] for w in words_list)
                                            lx1 = max(w.bbox[2] for w in words_list)
                                            ly1 = max(w.bbox[3] for w in words_list)
                                            page_lines.append(Line(words=words_list, bbox=(lx0, ly0, lx1, ly1)))
                                            
                        elif isinstance(element, (LTImage, LTFigure)):
                            img_cnt = count_images_recursive(element)
                            ibbox = (float(element.x0), float(height - element.y1), float(element.x1), float(height - element.y0))
                            if img_cnt > 0:
                                fig_type, fig_conf = HierarchyBuilder.classify_figure_type(ibbox, width, height, is_vector=False)
                                page_obj.images.append(ImageObj(
                                    bbox=ibbox,
                                    width=float(element.width),
                                    height=float(element.height),
                                    resolution="72x72 dpi",
                                    figure_type=fig_type,
                                    confidence=fig_conf
                                ))
                            if isinstance(element, LTFigure):
                                extracted["charts_figures_detected"] = True
                                fig_type, fig_conf = HierarchyBuilder.classify_figure_type(ibbox, width, height, is_vector=True, num_paths=5)
                                page_obj.charts.append(ChartObj(
                                    chart_type="Unknown Figure",
                                    bbox=ibbox,
                                    figure_type=fig_type,
                                    confidence=fig_conf
                                ))
                        elif isinstance(element, (LTCurve, LTLine, LTRect)):
                            extracted["charts_figures_detected"] = True
                            ibbox = (float(element.x0), float(height - element.y1), float(element.x1), float(height - element.y0))
                            fig_type, fig_conf = HierarchyBuilder.classify_figure_type(ibbox, width, height, is_vector=True, num_paths=1)
                            page_obj.charts.append(ChartObj(
                                chart_type="Unknown Figure",
                                bbox=ibbox,
                                figure_type=fig_type,
                                confidence=fig_conf
                            ))
                            
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
                    p_text_raw = "".join(page_text_blocks)
                    char_cnt = len(p_text_raw.strip())
                    word_cnt = len(p_text_raw.strip().split())
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
                    full_text_list.append("".join(page_text_blocks))
                except Exception as e:
                    extracted["warnings"].append(f"Page {page_num + 1}: Processing layout failed: {e}")
                    
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
            
            # Close layout device
            device.close()

        extracted["warnings"].append("Table extraction is unsupported by pdfminer.six")
        return extracted
