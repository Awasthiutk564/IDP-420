import time
import re
from typing import List, Dict, Any
from .stage import Stage
from utils.document_graph import DocumentNode, BlockNode
from utils.math_normalizer import is_likely_math, full_math_to_latex


class StageMath(Stage):
    """
    Pipeline stage: Mathematical Equation Extraction.

    For every text block on each page:
    1. Uses is_likely_math() from math_normalizer (Unicode-aware, sympy-backed)
       to detect equation blocks more accurately than the old regex approach.
    2. Promotes identified blocks to block_type="equation".
    3. Runs the EquationModel to generate LaTeX, MathML, and symbol trees.

    Improvements over v1:
    - Delegates math detection to the centralized math_normalizer utility,
      which handles Unicode superscripts, Greek letters, and common OCR
      artifacts before deciding if a block is math.
    - Passes is_digital flag correctly based on document_type.
    - Avoids false-positives from table-of-contents dots and long words.
    """

    def __init__(self):
        super().__init__(name="Mathematical Equation Extraction")

    def run(
        self,
        doc_graph: DocumentNode,
        pdf_path: str,
        adapters: List[Any],
        classifiers: Dict[str, Any],
        models: Dict[str, Any],
    ) -> DocumentNode:

        equation_model = models.get("equation")
        is_digital = (doc_graph.document_type != "Scanned")

        for page in doc_graph.pages:
            start_time = time.time()
            blocks = page.statistics.get("blocks", [])

            for block in blocks:
                text = block.text
                if not text or not text.strip():
                    continue

                # Skip already-classified non-text blocks
                if block.block_type in ("table", "figure", "chart", "image"):
                    continue

                # Use the centralised, Unicode-aware heuristic
                if is_likely_math(text):
                    block.block_type = "equation"

                    if equation_model:
                        # full_math_to_latex is called inside equation_model.run()
                        # via normalize_math_text -> extract_latex_from_sympy,
                        # but we still pass the raw text so the model can do it all.
                        latex, mathml, symbol_tree, prov = equation_model.run(
                            block_text=text,
                            is_digital=is_digital,
                        )
                        block.latex = latex
                        block.mathml = mathml
                        block.symbol_tree = symbol_tree
                        block.provenance = prov
                    else:
                        # Fallback: at least store normalized LaTeX
                        block.latex = full_math_to_latex(text)
                        block.mathml = ""
                        block.symbol_tree = {}
                        block.provenance = {
                            "library": "math_normalizer",
                            "version": "2.0",
                            "confidence": 0.70,
                            "fallback": True,
                        }

            page.statistics["processing_time"] += (time.time() - start_time)

        return doc_graph
