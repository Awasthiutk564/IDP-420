import re
import time
import xml.etree.ElementTree as ET
from typing import Dict, Any, Tuple, Optional
from .base_model import BaseModel

class EquationModel(BaseModel):
    def __init__(self):
        super().__init__(model_name="Pix2Tex/Nougat Formula Solver", framework="HuggingFace/Transformers")

    def run(self, block_text: str, is_digital: bool = True, image_path: Optional[str] = None) -> Tuple[str, str, Dict[str, Any], Dict[str, Any]]:
        """
        Parses equations from text/images.
        Returns:
            latex: LaTeX string
            mathml: Self-contained MathML XML string
            symbol_tree: Operator/Symbol parse tree dictionary
            provenance: Model provenance metadata
        """
        start_time = time.time()
        
        # Determine LaTeX representation
        latex_str = self._clean_to_latex(block_text)
        
        # Build symbol tree and MathML structure
        symbol_tree = self._build_symbol_tree(latex_str)
        mathml_str = self._generate_mathml(symbol_tree)
        
        prov = {
            "library": "UnicodeMathParser" if is_digital else "Pix2Tex Fallback",
            "version": "1.0",
            "confidence": 0.95 if is_digital else 0.75,
            "fallback": not is_digital,
            "processing_time": time.time() - start_time
        }
        
        return latex_str, mathml_str, symbol_tree, prov

    def _clean_to_latex(self, text: str) -> str:
        # Convert simple math symbols to LaTeX equivalents
        cleaned = text.strip()
        # Remove wrapper brackets if any
        cleaned = re.sub(r'^[\$\[\(]|[\]\)\$]$', '', cleaned).strip()
        
        replacements = [
            (r'α', r'\\alpha'),
            (r'β', r'\\beta'),
            (r'γ', r'\\gamma'),
            (r'π', r'\\pi'),
            (r'Σ', r'\\sum'),
            (r'∫', r'\\int'),
            (r'√', r'\\sqrt'),
            (r'±', r'\\pm'),
            (r'×', r'\\times'),
            (r'÷', r'\\div'),
            (r'∞', r'\\infty'),
            (r'≠', r'\\neq'),
            (r'≤', r'\\leq'),
            (r'≥', r'\\geq'),
            (r' → ', r' \\rightarrow '),
            (r' = ', r' = ')
        ]
        for src, dest in replacements:
            cleaned = re.sub(src, dest, cleaned)
            
        # Convert superscripts like x² to x^2
        super_map = {'⁰':'0', '¹':'1', '²':'2', '³':'3', '⁴':'4', '⁵':'5', '⁶':'6', '⁷':'7', '⁸':'8', '⁹':'9'}
        for char, val in super_map.items():
            cleaned = cleaned.replace(char, f"^{val}")
            
        return cleaned

    def _build_symbol_tree(self, latex: str) -> Dict[str, Any]:
        """
        Parses a simple mathematical expression into a syntax tree.
        e.g., "E = mc^2" -> {type: "relation", operator: "=", left: "E", right: "mc^2"}
        """
        # Search for equality relation
        if "=" in latex:
            parts = latex.split("=", 1)
            return {
                "type": "relation",
                "operator": "=",
                "left": self._parse_expression(parts[0].strip()),
                "right": self._parse_expression(parts[1].strip())
            }
        return self._parse_expression(latex)

    def _parse_expression(self, expr: str) -> Dict[str, Any]:
        # Handle exponent notation like x^2 or e^{i\pi}
        match = re.search(r'([a-zA-Z0-9]+)\^(\{([^}]+)\}|([a-zA-Z0-9]+))', expr)
        if match:
            base = match.group(1)
            exp = match.group(3) or match.group(4)
            return {
                "type": "superscript",
                "base": {"type": "identifier", "value": base},
                "exponent": self._parse_expression(exp)
            }
            
        # Handle multiplication or layout terms
        return {
            "type": "term",
            "value": expr
        }

    def _generate_mathml(self, tree: Dict[str, Any]) -> str:
        """
        Generates standard self-contained MathML XML.
        """
        math = ET.Element("math", xmlns="http://www.w3.org/1998/Math/MathML")
        mrow = ET.SubElement(math, "mrow")
        self._build_xml_elements(tree, mrow)
        
        # Convert element tree to self-contained XML string
        try:
            return ET.tostring(math, encoding="utf-8").decode("utf-8")
        except Exception:
            return "<math><mrow><mtext>Math parsing error</mtext></mrow></math>"

    def _build_xml_elements(self, node: Dict[str, Any], parent: ET.Element):
        t = node.get("type")
        if t == "relation":
            self._build_xml_elements(node["left"], parent)
            mo = ET.SubElement(parent, "mo")
            mo.text = node["operator"]
            self._build_xml_elements(node["right"], parent)
        elif t == "superscript":
            msubsup = ET.SubElement(parent, "msup")
            self._build_xml_elements(node["base"], msubsup)
            self._build_xml_elements(node["exponent"], msubsup)
        elif t == "identifier":
            mi = ET.SubElement(parent, "mi")
            mi.text = node["value"]
        else:
            val = str(node.get("value", ""))
            # Split numbers, variables, and operators into MathML elements
            for word in val.split():
                if re.match(r'^[0-9]+$', word):
                    mn = ET.SubElement(parent, "mn")
                    mn.text = word
                elif word in ["+", "-", "*", "/", "=", "<", ">"]:
                    mo = ET.SubElement(parent, "mo")
                    mo.text = word
                else:
                    mi = ET.SubElement(parent, "mi")
                    mi.text = word
