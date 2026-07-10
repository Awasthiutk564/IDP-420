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
                
                # Check if this block is contact info or metadata, or contains email, phone, or URL (Issue 1)
                is_contact = block.block_type in ["contact_info", "metadata", "page_number", "footnote"]
                has_email = bool(re.search(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', text))
                has_phone = bool(re.search(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', text))
                has_url = bool(re.search(r'https?://|www\.|github\.com|linkedin\.com', text, re.IGNORECASE))
                
                if is_contact or has_email or has_phone or has_url:
                    is_math = False
                else:
                    # Exclude TOC lines with leader dots
                    if "..." in text or " . . " in text:
                        is_math = False
                    else:
                        # Look for LaTeX expressions or math equations
                        # 1. Variables equal to numbers/expressions, e.g., x = 5, y = x + 2, E = mc^2, f(x) = ...
                        if re.search(r'\b[x-zX-Z]\s*=\s*[-+]?\d*\.?\d+', text):
                            is_math = True
                        elif re.search(r'\b[a-zA-Z]\s*[-+*/=]\s*[a-zA-Z0-9]', text) and not re.search(r'\b[a-zA-Z]{4,}\b', text): # Simple algebraic relations, avoiding natural language words
                            is_math = True
                        elif re.search(r'\b[a-zA-Z]\(x\)\s*=\s*', text): # f(x) = ...
                            is_math = True
                        # 2. LaTeX commands
                        elif re.search(r'\\(?:sum|int|prod|alpha|beta|gamma|delta|pi|sigma|theta|lambda|phi|psi|omega|sqrt|frac|begin|end|sin|cos|tan|log|ln|lim|partial|nabla)\b', text):
                            is_math = True
                        # 3. Explicit math superscript/subscript notation
                        elif re.search(r'[a-zA-Z0-9]\^[a-zA-Z0-9]', text) or re.search(r'[a-zA-Z0-9]_[a-zA-Z0-9]', text):
                            is_math = True
                        # 4. Standard Greek math letters & operators
                        elif any(sym in text for sym in ["α", "β", "γ", "π", "Σ", "∫", "√", "±", "×", "÷", "λ", "θ", "∞", "≈", "≠", "≤", "≥", "∂", "∇", "Δ", "Ω", "μ", "σ", "φ", "ψ", "ω", "∝", "≡"]):
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
