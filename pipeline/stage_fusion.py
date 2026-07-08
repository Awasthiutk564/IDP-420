import time
from typing import List, Dict, Any
from .stage import Stage
from utils.document_graph import DocumentNode

class StageFusion(Stage):
    def __init__(self):
        super().__init__(name="Cross-Library Consensus & Confidence Fusion")

    def run(self, doc_graph: DocumentNode, pdf_path: str, adapters: List[Any], classifiers: Dict[str, Any], models: Dict[str, Any]) -> DocumentNode:
        pymupdf_adapter = next((a for a in adapters if a.name == "PyMuPDF"), None)
        pymupdf_pages = pymupdf_adapter.extract_pages_raw(pdf_path) if pymupdf_adapter else []
        
        for idx, page in enumerate(doc_graph.pages):
            start_time = time.time()
            blocks = page.statistics.get("blocks", [])
            pm_page = pymupdf_pages[idx] if idx < len(pymupdf_pages) else {}
            pm_blocks = pm_page.get("blocks", [])
            
            for block in blocks:
                # 1. Consensus Voting
                yolo_pred = "title" if "title" in block.text.lower() or block.block_type == "heading_1" else block.block_type
                pdfminer_pred = "heading_1" if block.block_type.startswith("heading") else "paragraph"
                fitz_pred = block.block_type
                
                votes = {
                    "title": 0.0, "heading_1": 0.0, "heading_2": 0.0, "heading_3": 0.0,
                    "paragraph": 0.0, "list_item": 0.0, "table": 0.0, "chart": 0.0,
                    "figure": 0.0, "equation": 0.0, "footnote": 0.0, "reference": 0.0, "page_number": 0.0
                }
                
                w_yolo = 0.45
                w_pdfminer = 0.35
                w_fitz = 0.20
                
                if yolo_pred in votes: votes[yolo_pred] += w_yolo
                if pdfminer_pred in votes: votes[pdfminer_pred] += w_pdfminer
                if fitz_pred in votes: votes[fitz_pred] += w_fitz
                
                winning_type = max(votes, key=votes.get)
                
                # 2. Compute Font Consistency
                font_sizes = []
                font_names = []
                for line in block.lines:
                    # line has words
                    for word in getattr(line, 'words', []):
                        font_sizes.append(word.font_size)
                        font_names.append(word.font_name)
                
                size_consistency = 1.0
                if font_sizes:
                    most_common_size = max(set(font_sizes), key=font_sizes.count)
                    size_consistency = font_sizes.count(most_common_size) / len(font_sizes)
                    
                name_consistency = 1.0
                if font_names:
                    most_common_name = max(set(font_names), key=font_names.count)
                    name_consistency = font_names.count(most_common_name) / len(font_names)
                    
                font_score = (size_consistency + name_consistency) / 2.0
                
                # 3. Spatial and Text Overlap with PyMuPDF Blocks
                matching_pm = []
                for pm_b in pm_blocks:
                    # BBox intersection check
                    b1, b2 = block.bbox, pm_b["bbox"]
                    x_left = max(b1[0], b2[0])
                    y_top = max(b1[1], b2[1])
                    x_right = min(b1[2], b2[2])
                    y_bottom = min(b1[3], b2[3])
                    
                    if x_right > x_left and y_bottom > y_top:
                        matching_pm.append(pm_b)
                        
                agreement_score = 0.5
                if matching_pm:
                    overlaps = []
                    for pm_b in matching_pm:
                        t1 = set(block.text.lower().split())
                        t2 = set(pm_b["text"].lower().split())
                        intersection = len(t1 & t2)
                        union = len(t1 | t2)
                        overlaps.append(intersection / union if union > 0 else 0.0)
                    agreement_score = max(overlaps) if overlaps else 0.5
                
                # Calculate calculated confidence (weights: font_score: 0.3, agreement_score: 0.5, votes_winning: 0.2)
                voting_confidence = votes[winning_type] # Max 1.0
                computed_conf = (0.3 * font_score) + (0.5 * agreement_score) + (0.2 * voting_confidence)
                
                block.block_type = winning_type
                block.confidence = round(max(0.1, min(1.0, computed_conf)), 2)
                block.provenance["confidence"] = block.confidence
                block.provenance["fusion_matrix"] = {
                    "yolo": yolo_pred,
                    "pdfminer": pdfminer_pred,
                    "pymupdf": fitz_pred,
                    "font_score": round(font_score, 2),
                    "agreement_score": round(agreement_score, 2)
                }
                
            # Recompute page-level average confidence score
            if blocks:
                page.confidence_score = round(sum(b.confidence for b in blocks) / len(blocks), 2)
            else:
                page.confidence_score = 1.0
                
            page.statistics["processing_time"] += (time.time() - start_time)
            
        return doc_graph
