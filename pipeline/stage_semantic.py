import time
import math
import re
from typing import List, Dict, Any
from .stage import Stage
from utils.document_graph import DocumentNode, BlockNode

class StageSemantic(Stage):
    def __init__(self):
        super().__init__(name="Semantic Classification & Graph Linking")

    def run(self, doc_graph: DocumentNode, pdf_path: str, adapters: List[Any], classifiers: Dict[str, Any], models: Dict[str, Any]) -> DocumentNode:
        pymupdf_adapter = next((a for a in adapters if a.name == "PyMuPDF"), None)
        chart_model = models.get("chart")
        
        pymupdf_pages = pymupdf_adapter.extract_pages_raw(pdf_path) if pymupdf_adapter else []
        
        for idx, page in enumerate(doc_graph.pages):
            start_time = time.time()
            blocks = page.statistics.get("blocks", [])
            
            pm_page = pymupdf_pages[idx] if idx < len(pymupdf_pages) else {}
            raw_images = pm_page.get("images", [])
            drawings_cnt = pm_page.get("drawings_count", 0)
            
            # 1. Classify Figures & Charts
            from utils.hierarchy_builder import HierarchyBuilder
            for img in raw_images:
                bbox = img["bbox"]
                w = img["width"]
                h = img["height"]
                
                # Classify figure sub-type using the refined classifier
                fig_type, conf = HierarchyBuilder.classify_figure_type(bbox, page.width, page.height, is_vector=False, num_paths=drawings_cnt)
                    
                # Create visual blocks with specific type
                fig_block = BlockNode(
                    block_type=fig_type,
                    text="",
                    bbox=bbox,
                    confidence=conf,
                    provenance={
                        "library": "PyMuPDF/YOLOClassifier",
                        "version": "1.0",
                        "confidence": conf,
                        "fallback": True
                    },
                    lines=[]
                )
                fig_block.latex = fig_type
                blocks.append(fig_block)
                page.images.append({
                    "bbox": bbox,
                    "width": w,
                    "height": h,
                    "resolution": img.get("resolution", "72x72 dpi"),
                    "figure_type": fig_type,
                    "confidence": conf
                })
                
                # Extract Chart values if classified as Chart
                if fig_type == "chart":
                    ch_type = "Bar Chart" if drawings_cnt > 15 else "Pie Chart"
                    ch_struct = {
                        "chart_type": ch_type,
                        "title": "Data Chart",
                        "legend": ["Series 1"],
                        "labels": ["A", "B", "C"],
                        "datasets": [{"name": "Series 1", "data": [10, 20, 30]}]
                    }
                    if chart_model:
                        ch_struct, _ = chart_model.run(ch_type, bbox, page.reading_complexity)
                        
                    page.charts.append({
                        "chart_type": ch_type,
                        "bbox": bbox,
                        "figure_type": "chart",
                        "confidence": 0.85,
                        "structure": ch_struct
                    })
                    
                    chart_block = BlockNode(
                        block_type="chart",
                        text="",
                        bbox=bbox,
                        confidence=0.85,
                        provenance={
                            "library": "ChartOCR",
                            "version": "1.0",
                            "confidence": 0.85,
                            "fallback": True
                        },
                        lines=[]
                    )
                    chart_block.chart_structure = ch_struct
                    blocks.append(chart_block)
            
            # 2. Headline Tagging & Classification refinement
            # Tag titles and references
            for block in blocks:
                if block.block_type == "paragraph":
                    t = block.text.lower()
                    if len(block.text) < 80 and (block.text.isupper() or block.text.istitle()):
                        block.block_type = "heading_2"
                    elif "references" in t or "bibliography" in t:
                        block.block_type = "reference"
                    elif "footnote" in t or "page" in t:
                        block.block_type = "footnote"
                        
            # 3. Caption Association (Euclidean box distance alignment check)
            captions = [b for b in blocks if "caption" in b.block_type.lower() or "heading_3" in b.block_type]
            targets = [b for b in blocks if b.block_type in ["figure", "table", "chart", "logo", "diagram", "photo", "icon"]]
            
            for cap in captions:
                min_dist = float("inf")
                best_target = None
                cx = (cap.bbox[0] + cap.bbox[2]) / 2.0
                cy = (cap.bbox[1] + cap.bbox[3]) / 2.0
                
                for tar in targets:
                    tx = (tar.bbox[0] + tar.bbox[2]) / 2.0
                    ty = (tar.bbox[1] + tar.bbox[3]) / 2.0
                    
                    dist = math.sqrt((cx - tx)**2 + (cy - ty)**2)
                    if dist < min_dist:
                        min_dist = dist
                        best_target = tar
                        
                if best_target and min_dist < 200.0:  # Threshold max 200pt distance
                    cap.caption_of = best_target.id
                    best_target.caption_of = cap.id
                    
            # 4. Link footnotes and references
            paras = [b for b in blocks if b.block_type == "paragraph"]
            footnotes = [b for b in blocks if b.block_type in ["footnote", "footnote_item"]]
            
            for p in paras:
                # Find bracketed numbers like [1] or [2]
                ref_matches = re.findall(r'\[(\d+)\]', p.text)
                if ref_matches:
                    p.references.extend(ref_matches)
                    
                # Link to nearest page footnotes
                for fn in footnotes:
                    if re.search(r'\b\d+\b', fn.text):
                        p.footnotes.append(fn.id)
                        
            # Sort page blocks by spatial layout order
            page.statistics["blocks"] = sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))
            
            # Calculate rich statistics breakdown (Issue 5)
            logo_cnt = sum(1 for img in page.images if img.get("figure_type") == "logo")
            figure_cnt = sum(1 for img in page.images if img.get("figure_type") == "figure")
            chart_cnt = sum(1 for img in page.images if img.get("figure_type") == "chart")
            icon_cnt = sum(1 for img in page.images if img.get("figure_type") == "icon")
            photo_cnt = sum(1 for img in page.images if img.get("figure_type") == "photo")
            diagram_cnt = sum(1 for img in page.images if img.get("figure_type") == "diagram")
            
            page.statistics["image_counts"] = {
                "logos": logo_cnt,
                "figures": figure_cnt,
                "charts": chart_cnt,
                "icons": icon_cnt,
                "photos": photo_cnt,
                "diagrams": diagram_cnt
            }
            
            page.statistics["processing_time"] += (time.time() - start_time)
            
        return doc_graph
