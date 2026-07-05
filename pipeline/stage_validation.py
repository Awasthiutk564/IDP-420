import time
from typing import List, Dict, Any
from .stage import Stage
from utils.document_graph import DocumentNode

class StageValidation(Stage):
    def __init__(self):
        super().__init__(name="Validation Engine")

    def run(self, doc_graph: DocumentNode, pdf_path: str, adapters: List[Any], classifiers: Dict[str, Any], models: Dict[str, Any]) -> DocumentNode:
        for page in doc_graph.pages:
            start_time = time.time()
            blocks = page.statistics.get("blocks", [])
            
            warnings = []
            
            # 1. Heading Validation (No H2/H3 without an H1 check)
            has_h1 = any(b.block_type == "heading_1" for b in blocks)
            has_h2 = any(b.block_type == "heading_2" for b in blocks)
            if has_h2 and not has_h1:
                warnings.append("Validation Warning: Detected H2 headings without a preceding H1 title block.")

            # 2. Table row/col validation
            for tbl in page.tables:
                if tbl["rows"] <= 0 or tbl["columns"] <= 0:
                    warnings.append(f"Validation Warning: Table at {tbl['bbox']} returned zero dimension grid.")

            # 3. Mathematical MathML validation
            for block in blocks:
                if block.block_type == "equation":
                    if not block.latex or not block.mathml:
                        warnings.append(f"Validation Warning: Equation block {block.id} is missing LaTeX or MathML strings.")

            # 4. Reading Order Validation (overlap check)
            for i, b1 in enumerate(blocks):
                for b2 in blocks[i+1:]:
                    # Compute box overlap
                    box1, box2 = b1.bbox, b2.bbox
                    x_overlap = max(0, min(box1[2], box2[2]) - max(box1[0], box2[0]))
                    y_overlap = max(0, min(box1[3], box2[3]) - max(box1[1], box2[1]))
                    if x_overlap > 20.0 and y_overlap > 20.0:
                        # Only warn for significant overlapping text blocks
                        if b1.block_type == "paragraph" and b2.block_type == "paragraph":
                            warnings.append(f"Validation Warning: Bounding box overlap between paragraphs {b1.id} and {b2.id}.")

            page.statistics["warnings"].extend(warnings)
            page.statistics["processing_time"] += (time.time() - start_time)
            
        return doc_graph
