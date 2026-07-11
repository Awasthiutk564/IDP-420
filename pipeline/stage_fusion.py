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
                pdfminer_pred = "heading_1" if block.block_type.startswith("heading") else ("paragraph" if block.block_type not in ["logo", "icon", "photo", "diagram", "contact_info", "chart", "table", "equation", "footnote", "reference", "page_number"] else block.block_type)
                fitz_pred = block.block_type
                
                votes = {
                    "title": 0.0, "heading_1": 0.0, "heading_2": 0.0, "heading_3": 0.0,
                    "paragraph": 0.0, "list_item": 0.0, "table": 0.0, "chart": 0.0,
                    "figure": 0.0, "equation": 0.0, "footnote": 0.0, "reference": 0.0, "page_number": 0.0,
                    "logo": 0.0, "icon": 0.0, "photo": 0.0, "diagram": 0.0, "contact_info": 0.0
                }
                
                w_yolo = 0.45
                w_pdfminer = 0.35
                w_fitz = 0.20
                
                if yolo_pred in votes: votes[yolo_pred] += w_yolo
                if pdfminer_pred in votes: votes[pdfminer_pred] += w_pdfminer
                if fitz_pred in votes: votes[fitz_pred] += w_fitz
                
                winning_type = max(votes, key=votes.get)
                if block.block_type == "equation" or fitz_pred == "equation":
                    winning_type = "equation"
                
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
                
                # 4. Refined Confidence Scoring heuristics (Issue 6)
                unique_preds = len({yolo_pred, pdfminer_pred, fitz_pred})
                if unique_preds == 1:
                    extractor_agreement = 1.0
                elif unique_preds == 2:
                    extractor_agreement = 0.75
                else:
                    extractor_agreement = 0.4
                    
                is_block_bold = any(word.font_style == "Bold" for line in block.lines for word in getattr(line, 'words', []))
                if winning_type.startswith("heading") or winning_type == "title":
                    bold_score = 1.0 if is_block_bold else 0.5
                else:
                    bold_score = 1.0 if not is_block_bold else 0.7
                    
                base_size = 10.0
                if font_sizes:
                    avg_block_size = sum(font_sizes) / len(font_sizes)
                    if winning_type == "heading_1" or winning_type == "title":
                        size_heuristic_score = 1.0 if avg_block_size >= base_size + 4.0 else 0.5
                    elif winning_type == "heading_2":
                        size_heuristic_score = 1.0 if avg_block_size >= base_size + 2.0 else 0.6
                    elif winning_type == "heading_3":
                        size_heuristic_score = 1.0 if avg_block_size >= base_size + 0.8 else 0.7
                    else:
                        size_heuristic_score = 1.0 if avg_block_size <= base_size + 1.5 else 0.6
                else:
                    size_heuristic_score = 0.8
                    
                voting_confidence = votes[winning_type]
                computed_conf = (0.20 * font_score) + \
                                (0.25 * agreement_score) + \
                                (0.20 * voting_confidence) + \
                                (0.15 * extractor_agreement) + \
                                (0.10 * bold_score) + \
                                (0.10 * size_heuristic_score)
                # Override to normalize heading confidence when no ambiguity exists (Issue 5)
                if winning_type.startswith("heading") or winning_type in ["title", "contact_info"]:
                    if font_score >= 0.8 and extractor_agreement >= 0.75:
                        computed_conf = 0.95
                        
                block.block_type = winning_type
                block.confidence = round(round(max(0.0, min(1.0, computed_conf)) * 20) / 20, 2)
                block.provenance["confidence"] = block.confidence
                block.provenance["fusion_matrix"] = {
                    "yolo": yolo_pred,
                    "pdfminer": pdfminer_pred,
                    "pymupdf": fitz_pred,
                    "font_score": round(font_score, 2),
                    "agreement_score": round(agreement_score, 2),
                    "bold_score": bold_score,
                    "size_heuristic_score": size_heuristic_score
                }
                
            # Recompute page-level average confidence score
            if blocks:
                page.confidence_score = round(sum(b.confidence for b in blocks) / len(blocks), 2)
            else:
                page.confidence_score = 1.0
                
            # Rebuild final parent-child hierarchy on page blocks (Issue 3 & 4)
            curr_h1 = None
            curr_h2 = None
            curr_h3 = None
            curr_list_item = None
            
            # Sort them spatially first to ensure correct sequential hierarchy
            blocks = sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))
            page.statistics["blocks"] = blocks
            
            for bn in blocks:
                bn.parent_id = None
                
                # Convert bulleted sub-list items under role/project titles to paragraph blocks
                if bn.block_type == "list_item":
                    has_bullet = bn.text.strip().startswith(('●', '•', '-', '*', '✓', '➤', '○', '▪', '■', '◦', '–'))
                    if has_bullet and curr_list_item and not curr_list_item.text.strip().startswith(('●', '•', '-', '*', '✓', '➤', '○', '▪', '■', '◦', '–')):
                        bn.block_type = "paragraph"
                        bn.parent_id = curr_list_item.id
                        continue
                
                if bn.block_type == "heading_1":
                    curr_h1 = bn
                    curr_h2 = None
                    curr_h3 = None
                    curr_list_item = None
                elif bn.block_type == "heading_2":
                    curr_h2 = bn
                    curr_h3 = None
                    curr_list_item = None
                    if curr_h1:
                        bn.parent_id = curr_h1.id
                elif bn.block_type == "heading_3":
                    curr_h3 = bn
                    curr_list_item = None
                    if curr_h2:
                        bn.parent_id = curr_h2.id
                    elif curr_h1:
                        bn.parent_id = curr_h1.id
                elif bn.block_type == "list_item":
                    curr_list_item = bn
                    active_parent = curr_h3 or curr_h2 or curr_h1
                    if active_parent:
                        bn.parent_id = active_parent.id
                else:
                    if curr_list_item and bn.block_type == "paragraph":
                        bn.parent_id = curr_list_item.id
                    else:
                        active_parent = curr_h3 or curr_h2 or curr_h1
                        if active_parent:
                            bn.parent_id = active_parent.id
                            
            page.statistics["processing_time"] += (time.time() - start_time)
            
        return doc_graph
