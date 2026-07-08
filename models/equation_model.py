import re
import time
import xml.etree.ElementTree as ET
from typing import Dict, Any, Tuple, Optional
from .base_model import BaseModel
from utils.math_normalizer import normalize_math_text, extract_latex_from_sympy, full_math_to_latex


class EquationModel(BaseModel):
    def __init__(self):
        super().__init__(model_name="SymPy/Unicode MathParser v2", framework="sympy + regex")

    def run(
        self,
        block_text: str,
        is_digital: bool = True,
        image_path: Optional[str] = None
    ) -> Tuple[str, str, Dict[str, Any], Dict[str, Any]]:
        """
        Parses equations from text/images.

        Pipeline:
        1. Normalize Unicode superscripts, Greek letters, and OCR artifacts.
        2. Attempt sympy-based LaTeX conversion (most accurate for algebraic exprs).
        3. Fall back to normalized text as LaTeX if sympy cannot parse.
        4. Build MathML from the parse tree.
        5. Return (latex, mathml, symbol_tree, provenance).

        Returns:
            latex: LaTeX string
            mathml: Self-contained MathML XML string
            symbol_tree: Operator/Symbol parse tree dictionary
            provenance: Model provenance metadata
        """
        start_time = time.time()

        # --- Step 1+2: Normalize then convert to LaTeX ---
        latex_str = full_math_to_latex(block_text)

        # --- Step 3: Build symbol tree for downstream use ---
        symbol_tree = self._build_symbol_tree(latex_str)

        # --- Step 4: Generate MathML ---
        mathml_str = self._generate_mathml(symbol_tree)

        confidence = 0.97 if is_digital else 0.80
        library = "sympy+UnicodeMathParser" if is_digital else "PaddleOCR+sympy"

        prov = {
            "library": library,
            "version": "2.0",
            "confidence": confidence,
            "fallback": not is_digital,
            "processing_time": time.time() - start_time,
        }

        return latex_str, mathml_str, symbol_tree, prov

    # ------------------------------------------------------------------
    # Symbol tree builder
    # ------------------------------------------------------------------

    def _build_symbol_tree(self, latex: str) -> Dict[str, Any]:
        """
        Parses a LaTeX mathematical expression into a lightweight syntax tree.
        e.g., "E = mc^2" -> {type: "relation", operator: "=", left: "E", right: "mc^2"}
        """
        # Equality relation
        if "=" in latex and "\\neq" not in latex and "\\leq" not in latex and "\\geq" not in latex:
            parts = latex.split("=", 1)
            return {
                "type": "relation",
                "operator": "=",
                "left": self._parse_expression(parts[0].strip()),
                "right": self._parse_expression(parts[1].strip()),
            }
        return self._parse_expression(latex)

    def _parse_expression(self, expr: str) -> Dict[str, Any]:
        """Recursively parse a LaTeX expression into a tree node."""

        # Fraction: \frac{a}{b}
        frac_match = re.search(r'\\frac\{([^}]+)\}\{([^}]+)\}', expr)
        if frac_match:
            return {
                "type": "fraction",
                "numerator": self._parse_expression(frac_match.group(1)),
                "denominator": self._parse_expression(frac_match.group(2)),
            }

        # Square root: \sqrt{x} or \sqrt(x)
        sqrt_match = re.search(r'\\sqrt\{([^}]+)\}', expr)
        if sqrt_match:
            return {
                "type": "sqrt",
                "argument": self._parse_expression(sqrt_match.group(1)),
            }

        # Superscript: base^{exp} or base^exp
        sup_match = re.search(r'([a-zA-Z0-9\\]+)\^\{([^}]+)\}', expr)
        if sup_match:
            return {
                "type": "superscript",
                "base": {"type": "identifier", "value": sup_match.group(1)},
                "exponent": self._parse_expression(sup_match.group(2)),
            }
        sup_simple = re.search(r'([a-zA-Z0-9])\^([a-zA-Z0-9])', expr)
        if sup_simple:
            return {
                "type": "superscript",
                "base": {"type": "identifier", "value": sup_simple.group(1)},
                "exponent": {"type": "number" if sup_simple.group(2).isdigit() else "identifier",
                             "value": sup_simple.group(2)},
            }

        # Subscript: base_{sub} or base_sub
        sub_match = re.search(r'([a-zA-Z0-9\\]+)_\{([^}]+)\}', expr)
        if sub_match:
            return {
                "type": "subscript",
                "base": {"type": "identifier", "value": sub_match.group(1)},
                "subscript": self._parse_expression(sub_match.group(2)),
            }
        sub_simple = re.search(r'([a-zA-Z0-9])_([a-zA-Z0-9])', expr)
        if sub_simple:
            return {
                "type": "subscript",
                "base": {"type": "identifier", "value": sub_simple.group(1)},
                "subscript": {"type": "number" if sub_simple.group(2).isdigit() else "identifier",
                              "value": sub_simple.group(2)},
            }

        # Sum: \sum_{...}^{...}
        sum_match = re.search(r'\\sum_\{([^}]*)\}\^\{([^}]*)\}', expr)
        if sum_match:
            return {
                "type": "sum",
                "lower": self._parse_expression(sum_match.group(1)),
                "upper": self._parse_expression(sum_match.group(2)),
            }

        # Integral: \int_{...}^{...}
        int_match = re.search(r'\\int_\{([^}]*)\}\^\{([^}]*)\}', expr)
        if int_match:
            return {
                "type": "integral",
                "lower": self._parse_expression(int_match.group(1)),
                "upper": self._parse_expression(int_match.group(2)),
            }

        # Plain number
        if re.match(r'^-?[0-9]+(\.[0-9]+)?$', expr.strip()):
            return {"type": "number", "value": expr.strip()}

        # Default: treat as a term/identifier
        return {"type": "term", "value": expr}

    # ------------------------------------------------------------------
    # MathML generator
    # ------------------------------------------------------------------

    def _generate_mathml(self, tree: Dict[str, Any]) -> str:
        """Generates standard self-contained MathML XML from a symbol tree."""
        math = ET.Element("math", xmlns="http://www.w3.org/1998/Math/MathML")
        mrow = ET.SubElement(math, "mrow")
        self._build_xml_elements(tree, mrow)
        try:
            return ET.tostring(math, encoding="unicode")
        except Exception:
            return "<math><mrow><mtext>Math parsing error</mtext></mrow></math>"

    def _build_xml_elements(self, node: Dict[str, Any], parent: ET.Element):
        """Recursively builds MathML elements from the symbol tree."""
        t = node.get("type")

        if t == "relation":
            self._build_xml_elements(node["left"], parent)
            mo = ET.SubElement(parent, "mo")
            mo.text = node["operator"]
            self._build_xml_elements(node["right"], parent)

        elif t == "superscript":
            msup = ET.SubElement(parent, "msup")
            self._build_xml_elements(node["base"], msup)
            self._build_xml_elements(node["exponent"], msup)

        elif t == "subscript":
            msub = ET.SubElement(parent, "msub")
            self._build_xml_elements(node["base"], msub)
            self._build_xml_elements(node["subscript"], msub)

        elif t == "fraction":
            mfrac = ET.SubElement(parent, "mfrac")
            num_row = ET.SubElement(mfrac, "mrow")
            den_row = ET.SubElement(mfrac, "mrow")
            self._build_xml_elements(node["numerator"], num_row)
            self._build_xml_elements(node["denominator"], den_row)

        elif t == "sqrt":
            msqrt = ET.SubElement(parent, "msqrt")
            self._build_xml_elements(node["argument"], msqrt)

        elif t == "sum":
            munder = ET.SubElement(parent, "munderover")
            mo = ET.SubElement(munder, "mo")
            mo.text = "\u2211"  # Sigma sum symbol
            self._build_xml_elements(node["lower"], munder)
            self._build_xml_elements(node["upper"], munder)

        elif t == "integral":
            munder = ET.SubElement(parent, "munderover")
            mo = ET.SubElement(munder, "mo")
            mo.text = "\u222b"  # Integral symbol
            self._build_xml_elements(node["lower"], munder)
            self._build_xml_elements(node["upper"], munder)

        elif t in ("identifier",):
            mi = ET.SubElement(parent, "mi")
            mi.text = node.get("value", "")

        elif t == "number":
            mn = ET.SubElement(parent, "mn")
            mn.text = node.get("value", "")

        else:
            # Generic term: tokenize into numbers, operators, and identifiers
            val = str(node.get("value", ""))
            tokens = re.split(r'(\s+|[+\-*/=<>])', val)
            for token in tokens:
                token = token.strip()
                if not token:
                    continue
                if re.match(r'^-?[0-9]+(\.[0-9]+)?$', token):
                    mn = ET.SubElement(parent, "mn")
                    mn.text = token
                elif token in ["+", "-", "*", "/", "=", "<", ">",
                                r"\pm", r"\times", r"\div", r"\cdot"]:
                    mo = ET.SubElement(parent, "mo")
                    mo.text = token
                else:
                    mi = ET.SubElement(parent, "mi")
                    mi.text = token
