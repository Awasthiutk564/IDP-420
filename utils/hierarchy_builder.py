import re
from typing import List, Dict, Any, Tuple, Optional

class Word:
    def __init__(self, text: str, bbox: Tuple[float, float, float, float], font_name: str = "Unknown", font_size: float = 10.0, font_style: str = "Regular", color: str = "#000000", confidence: float = 1.0):
        self.text = text
        self.bbox = bbox  # (x0, y0, x1, y1)
        self.font_name = font_name
        self.font_size = font_size
        self.font_style = font_style
        self.color = color
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "bbox": self.bbox,
            "font_name": self.font_name,
            "font_size": self.font_size,
            "font_style": self.font_style,
            "color": self.color,
            "confidence": round(self.confidence, 2)
        }

class Line:
    def __init__(self, words: List[Word], bbox: Tuple[float, float, float, float] = (0,0,0,0), confidence: float = 1.0):
        self.words = words
        self.bbox = bbox if bbox != (0,0,0,0) else self._calculate_bbox()
        self.text = " ".join([w.text for w in self.words])
        self.confidence = confidence

    def _calculate_bbox(self) -> Tuple[float, float, float, float]:
        if not self.words:
            return (0, 0, 0, 0)
        x0 = min(w.bbox[0] for w in self.words)
        y0 = min(w.bbox[1] for w in self.words)
        x1 = max(w.bbox[2] for w in self.words)
        y1 = max(w.bbox[3] for w in self.words)
        return (x0, y0, x1, y1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "bbox": self.bbox,
            "confidence": round(self.confidence, 2),
            "words": [w.to_dict() for w in self.words]
        }

class Block:
    def __init__(self, block_type: str, lines: List[Line], bbox: Tuple[float, float, float, float] = (0,0,0,0), confidence: float = 1.0):
        self.block_type = block_type  # heading_1, heading_2, heading_3, paragraph, bullet_list_item, numbered_list_item, footnote, caption
        self.lines = lines
        self.bbox = bbox if bbox != (0,0,0,0) else self._calculate_bbox()
        self.text = "\n".join([l.text for l in self.lines])
        self.confidence = confidence

    def _calculate_bbox(self) -> Tuple[float, float, float, float]:
        if not self.lines:
            return (0, 0, 0, 0)
        x0 = min(l.bbox[0] for l in self.lines)
        y0 = min(l.bbox[1] for l in self.lines)
        x1 = max(l.bbox[2] for l in self.lines)
        y1 = max(l.bbox[3] for l in self.lines)
        return (x0, y0, x1, y1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_type": self.block_type,
            "bbox": self.bbox,
            "text": self.text,
            "confidence": round(self.confidence, 2),
            "lines": [l.to_dict() for l in self.lines]
        }

class Section:
    def __init__(self, section_type: str, bbox: Tuple[float, float, float, float], blocks: List[Block]):
        self.section_type = section_type  # header, footer, body, sidebar, caption_association
        self.bbox = bbox
        self.blocks = blocks

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_type": self.section_type,
            "bbox": self.bbox,
            "blocks": [b.to_dict() for b in self.blocks]
        }

class Table:
    def __init__(self, rows: int, columns: int, bbox: Tuple[float, float, float, float], confidence: float = 1.0, caption: str = "") -> None:
        self.rows = rows
        self.columns = columns
        self.bbox = bbox
        self.confidence = confidence
        self.caption = caption

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rows": self.rows,
            "columns": self.columns,
            "bbox": self.bbox,
            "confidence": round(self.confidence, 2),
            "caption": self.caption
        }

class ImageObj:
    def __init__(self, bbox: Tuple[float, float, float, float], width: float, height: float, resolution: str, figure_type: str = "photo", caption: str = "", confidence: float = 1.0) -> None:
        self.bbox = bbox
        self.width = width
        self.height = height
        self.resolution = resolution
        self.figure_type = figure_type  # photo, logo, icon, chart, diagram, illustration
        self.caption = caption
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bbox": self.bbox,
            "width": self.width,
            "height": self.height,
            "resolution": self.resolution,
            "figure_type": self.figure_type,
            "caption": self.caption,
            "confidence": round(self.confidence, 2)
        }

class ChartObj:
    def __init__(self, chart_type: str, bbox: Tuple[float, float, float, float], figure_type: str = "chart", caption: str = "", confidence: float = 1.0) -> None:
        self.chart_type = chart_type  # Bar Chart, Pie Chart, etc.
        self.bbox = bbox
        self.figure_type = figure_type
        self.caption = caption
        self.confidence = confidence

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chart_type": self.chart_type,
            "bbox": self.bbox,
            "figure_type": self.figure_type,
            "caption": self.caption,
            "confidence": round(self.confidence, 2)
        }

class HyperlinkObj:
    def __init__(self, url: str, bbox: Tuple[float, float, float, float]):
        self.url = url
        self.bbox = bbox

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "bbox": self.bbox
        }

class PageObj:
    def __init__(self, page_number: int, width: float, height: float):
        self.page_number = page_number
        self.width = width
        self.height = height
        self.reading_complexity = "Single column"
        self.document_quality = "Digitally generated"
        self.sections: List[Section] = []
        self.tables: List[Table] = []
        self.images: List[ImageObj] = []
        self.charts: List[ChartObj] = []
        self.hyperlinks: List[HyperlinkObj] = []
        self.footnotes: List[str] = []
        self.headers: List[str] = []
        self.footers: List[str] = []
        self.page_numbers: List[str] = []
        self.fonts: List[Dict[str, Any]] = []
        self.word_count = 0
        self.char_count = 0
        self.ocr_recommended = False
        self.confidence_score = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "width": self.width,
            "height": self.height,
            "reading_complexity": self.reading_complexity,
            "document_quality": self.document_quality,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "ocr_recommended": self.ocr_recommended,
            "confidence_score": round(self.confidence_score, 2),
            "fonts": self.fonts,
            "headers": self.headers,
            "footers": self.footers,
            "page_numbers": self.page_numbers,
            "footnotes": self.footnotes,
            "sections": [s.to_dict() for s in self.sections],
            "tables": [t.to_dict() for t in self.tables],
            "images": [i.to_dict() for i in self.images],
            "charts": [c.to_dict() for c in self.charts],
            "hyperlinks": [h.to_dict() for h in self.hyperlinks]
        }

class DocumentObj:
    def __init__(self, filename: str, metadata: Dict[str, Any]):
        self.filename = filename
        self.metadata = {k: str(v) if v is not None else "Unknown" for k, v in metadata.items()}
        self.page_count = 0
        self.pages: List[PageObj] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "metadata": self.metadata,
            "page_count": self.page_count,
            "pages": [p.to_dict() for p in self.pages]
        }


# ==========================================
# Hierarchy Builder Heuristic Processor
# ==========================================

class HierarchyBuilder:
    @staticmethod
    def detect_layout_columns(lines: List[Line], page_width: float) -> Tuple[int, str]:
        """Detect column layout type and return count + label."""
        if not lines or page_width <= 0:
            return 1, "Single column"
        
        mid = page_width / 2.0
        left_count = 0
        right_count = 0
        overlap_count = 0
        
        for line in lines:
            x0, _, x1, _ = line.bbox
            if x1 <= mid + 20:
                left_count += 1
            elif x0 >= mid - 20:
                right_count += 1
            else:
                overlap_count += 1
                
        total = left_count + right_count + overlap_count
        if total == 0:
            return 1, "Single column"
            
        if left_count > 0.3 * total and right_count > 0.3 * total:
            if overlap_count < 0.2 * total:
                return 2, "Double column"
            else:
                return 2, "Mixed layout"
        elif left_count > 0.1 * total and right_count > 0.1 * total and overlap_count > 0.4 * total:
            return 2, "Magazine layout"
            
        return 1, "Single column"

    @staticmethod
    def extract_reading_order(lines: List[Line], columns: int, page_width: float) -> List[Line]:
        """Sort lines to respect vertical columns flow rather than standard horizontal sweep."""
        if columns <= 1:
            return sorted(lines, key=lambda l: (l.bbox[1], l.bbox[0]))
            
        # Two-column layout flow: separate left and right
        mid = page_width / 2.0
        left_col = []
        right_col = []
        header_footer = []
        
        for line in lines:
            x0, y0, x1, y1 = line.bbox
            # Header or footer lines (spanning across column margin or at extreme top/bottom)
            if (y1 < 80 or y0 > 700) and (x0 < mid - 20 and x1 > mid + 20):
                header_footer.append(line)
            elif x1 <= mid + 15:
                left_col.append(line)
            elif x0 >= mid - 15:
                right_col.append(line)
            else:
                # If it crosses mid but isn't header/footer, assign to left or right based on center of mass
                cx = (x0 + x1) / 2.0
                if cx < mid:
                    left_col.append(line)
                else:
                    right_col.append(line)
                    
        # Sort left column top-to-bottom
        left_sorted = sorted(left_col, key=lambda l: (l.bbox[1], l.bbox[0]))
        # Sort right column top-to-bottom
        right_sorted = sorted(right_col, key=lambda l: (l.bbox[1], l.bbox[0]))
        # Sort headers top-to-bottom, footers bottom-to-bottom
        headers = sorted([l for l in header_footer if l.bbox[1] < 150], key=lambda l: l.bbox[1])
        footers = sorted([l for l in header_footer if l.bbox[1] >= 150], key=lambda l: l.bbox[1])
        
        return headers + left_sorted + right_sorted + footers

    @staticmethod
    def classify_headings_and_blocks(lines: List[Line], base_size: float, page_height: float) -> List[Block]:
        """Group adjacent lines into paragraphs or lists, detecting headings dynamically."""
        if not lines:
            return []
            
        blocks: List[Block] = []
        current_lines: List[Line] = []
        current_type = None
        
        def commit_block():
            nonlocal current_lines, current_type
            if not current_lines:
                return
            conf = 0.95
            if current_type.startswith("heading"):
                conf = 0.85
            elif current_type == "footnote":
                conf = 0.90
            elif current_type == "caption":
                conf = 0.90
            blocks.append(Block(block_type=current_type, lines=current_lines, confidence=conf))
            current_lines = []
            current_type = None

        for idx, line in enumerate(lines):
            text = line.text.strip()
            if not text:
                continue
                
            line_sizes = [w.font_size for w in line.words if w.font_size > 0]
            avg_size = sum(line_sizes) / len(line_sizes) if line_sizes else base_size
            styles = [w.font_style for w in line.words]
            is_bold = any(s == "Bold" for s in styles) or avg_size > base_size + 2.0
            
            # 1. Page numbers / footnotes detection
            x0, y0, x1, y1 = line.bbox
            if y1 > page_height * 0.86 and avg_size < base_size - 0.8:
                commit_block()
                current_lines.append(line)
                current_type = "footnote"
                commit_block()
                continue
                
            if len(text) < 10 and re.match(r'^(page\s+)?\d+(\s+of\s+\d+)?$', text.lower()):
                if y0 < page_height * 0.08 or y1 > page_height * 0.92:
                    commit_block()
                    current_lines.append(line)
                    current_type = "page_number"
                    commit_block()
                    continue
                    
            # 2. Caption detection
            if re.match(r'^(fig|figure|table|chart|fig\.)\s+\d+', text, re.IGNORECASE):
                commit_block()
                current_lines.append(line)
                current_type = "caption"
                commit_block()
                continue
                
            # 3. Headings detection based on size, bold, spacing, and casing
            if avg_size >= base_size + 1.2 or (is_bold and len(text) < 120 and not text.endswith('.')):
                commit_block()
                current_lines.append(line)
                if avg_size >= base_size + 5.0:
                    current_type = "heading_1"
                elif avg_size >= base_size + 2.5:
                    current_type = "heading_2"
                else:
                    current_type = "heading_3"
                commit_block()
                continue
                
            # 4. List items detection
            is_bullet = text.startswith(('•', '▪', '-', '*'))
            is_numbered = bool(re.match(r'^\d+[\.\)]', text) or re.match(r'^[a-zA-Z][\.\)]', text))
            
            if is_bullet:
                commit_block()
                current_lines.append(line)
                current_type = "bullet_list_item"
                commit_block()
                continue
            elif is_numbered:
                commit_block()
                current_lines.append(line)
                current_type = "numbered_list_item"
                commit_block()
                continue
                
            # 5. General paragraph text grouping
            if current_type == "paragraph":
                prev_line = current_lines[-1]
                v_dist = line.bbox[1] - prev_line.bbox[3]
                line_height = prev_line.bbox[3] - prev_line.bbox[1]
                if v_dist < 2.0 * max(line_height, 6.0):
                    current_lines.append(line)
                else:
                    commit_block()
                    current_lines.append(line)
                    current_type = "paragraph"
            else:
                commit_block()
                current_lines.append(line)
                current_type = "paragraph"
                
        commit_block()
        return blocks

    @staticmethod
    def classify_figure_type(bbox: Tuple[float, float, float, float], page_width: float, page_height: float, is_vector: bool = False, num_paths: int = 0) -> Tuple[str, float]:
        """Classify page figure element into precise sub-categories."""
        x0, y0, x1, y1 = bbox
        w = x1 - x0
        h = y1 - y0
        area = w * h
        
        if w < 32 and h < 32:
            return "icon", 0.95
            
        if (y0 < page_height * 0.12 or y1 > page_height * 0.88) and w < 160 and h < 80:
            return "logo", 0.85
            
        if is_vector or num_paths > 0:
            if num_paths >= 10:
                return "chart", 0.90
            elif num_paths > 0:
                return "diagram", 0.80
            else:
                return "illustration", 0.75
                
        if area > 45000:
            return "photo", 0.92
        else:
            return "illustration", 0.70

    @staticmethod
    def associate_captions(blocks: List[Block], page_obj: PageObj):
        """Associate caption blocks to the nearest table, image, or chart object."""
        captions = [b for b in blocks if b.block_type == "caption"]
        if not captions:
            return
            
        for cap in captions:
            cap_text = cap.text
            cx = (cap.bbox[0] + cap.bbox[2]) / 2.0
            cy = (cap.bbox[1] + cap.bbox[3]) / 2.0
            
            nearest_obj = None
            min_dist = float('inf')
            
            for tbl in page_obj.tables:
                tx = (tbl.bbox[0] + tbl.bbox[2]) / 2.0
                ty = (tbl.bbox[1] + tbl.bbox[3]) / 2.0
                dist = (cx - tx)**2 + (cy - ty)**2
                if dist < min_dist:
                    min_dist = dist
                    nearest_obj = tbl
                    
            for img in page_obj.images:
                ix = (img.bbox[0] + img.bbox[2]) / 2.0
                iy = (img.bbox[1] + img.bbox[3]) / 2.0
                dist = (cx - ix)**2 + (cy - iy)**2
                if dist < min_dist:
                    min_dist = dist
                    nearest_obj = img
                    
            for ch in page_obj.charts:
                cx_c = (ch.bbox[0] + ch.bbox[2]) / 2.0
                cy_c = (ch.bbox[1] + ch.bbox[3]) / 2.0
                dist = (cx - cx_c)**2 + (cy - cy_c)**2
                if dist < min_dist:
                    min_dist = dist
                    nearest_obj = ch
                    
            if nearest_obj and min_dist < 90000:
                nearest_obj.caption = cap_text

    @staticmethod
    def process_header_footers_cross_pages(pages: List[PageObj]):
        """Detect and group running headers, footers and repeated titles dynamically across pages."""
        if len(pages) < 2:
            return
            
        top_candidates = []
        bottom_candidates = []
        
        for p in pages:
            for s in p.sections:
                if s.section_type == "header":
                    top_candidates.extend([b.text.strip() for b in s.blocks])
                elif s.section_type == "footer":
                    bottom_candidates.extend([b.text.strip() for b in s.blocks])
                    
        top_repeats = {text for text in set(top_candidates) if top_candidates.count(text) >= 2}
        bottom_repeats = {text for text in set(bottom_candidates) if bottom_candidates.count(text) >= 2}
        
        for p in pages:
            for s in p.sections:
                for b in s.blocks:
                    if s.section_type == "header" and b.text.strip() in top_repeats:
                        p.headers.append(b.text.strip())
                    elif s.section_type == "footer" and b.text.strip() in bottom_repeats:
                        p.footers.append(b.text.strip())
                        
            for s in p.sections:
                for b in s.blocks:
                    txt = b.text.strip()
                    if b.block_type == "page_number" or re.match(r'^\d+$', txt) or "page" in txt.lower():
                        if txt not in p.page_numbers:
                            p.page_numbers.append(txt)
