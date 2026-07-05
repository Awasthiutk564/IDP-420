import time
import re
from typing import List, Dict, Any
from .stage import Stage
from utils.document_graph import DocumentNode, BlockNode

class StageMath(Stage):
    def __init__(self):
        super().__init__(name="Mathematical Equation Extraction")

    def run(self, doc_graph: DocumentNode, pdf_path: str, adapters: List[Any], classifiers: Dict[str, Any], models: Dict[str, Any]) -> DocumentNode:
        equation_model = models.get("equation")
        
        for page in doc_graph.pages:
            start_time = time.time()
            blocks = page.statistics.get("blocks", [])
            
            for block in blocks:
                # Detect equations based on math symbol heuristic
                text = block.text
                is_math = False
                
                # Exclude TOC lines with leader dots
                if "..." in text or " . . " in text:
                    is_math = False
                else:
                    # Look for LaTeX expressions or math equations
                    if re.search(r'\b[x-yX-Y]\s*=\s*[-+]?\d*\.?\d+', text):
                        is_math = True
                    elif re.search(r'\\(?:sum|int|prod|alpha|beta|gamma|delta|pi|sigma|theta|lambda|phi|psi|omega|sqrt|frac|begin|end)\b', text):
                        is_math = True
                    elif re.search(r'\b[a-zA-Z]\s*[-+*=]\s*[a-zA-Z0-9]', text):
                        is_math = True
                    elif any(sym in text for sym in ["α", "β", "γ", "π", "Σ", "∫", "√", "±", "×", "÷", "λ", "θ", "∞", "≈", "≠", "≤", "≥", "∂", "∇"]):
                        if re.search(r'\d|[a-zA-Z]', text):
                            is_math = True
                        
                if is_math:
                    block.block_type = "equation"
                    # Run equation model
                    if equation_model:
                        latex, mathml, symbol_tree, prov = equation_model.run(
                            block_text=text, 
                            is_digital=(doc_graph.document_type != "Scanned")
                        )
                        block.latex = latex
                        block.mathml = mathml
                        block.symbol_tree = symbol_tree
                        block.provenance = prov
                        
            page.statistics["processing_time"] += (time.time() - start_time)
            
        return doc_graph
