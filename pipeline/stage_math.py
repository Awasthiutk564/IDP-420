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
            
            is_image_ocr = page.statistics.get("is_image_ocr", False) or doc_graph.document_type == "Image OCR"
            if is_image_ocr:
                math_blocks = []
                non_math_blocks = []
                for b in blocks:
                    text = b.text.strip()
                    is_block_math = False
                    if any(sym in text for sym in ["∫", "∬", "Σ", "√", "π", "α", "β", "γ", "dx", "dy", "dt", "/"]) or \
                       any(op in text for op in ["+", "-", "*", "=", "^", "_"]) or \
                       re.search(r'\bx\b|\by\b', text) or \
                       "²" in text or "³" in text or text == "dx":
                        is_block_math = True
                    if is_block_math:
                        math_blocks.append(b)
                    else:
                        non_math_blocks.append(b)

                if math_blocks:
                    x0 = min(b.bbox[0] for b in math_blocks)
                    y0 = min(b.bbox[1] for b in math_blocks)
                    x1 = max(b.bbox[2] for b in math_blocks)
                    y1 = max(b.bbox[3] for b in math_blocks)
                    union_bbox = (x0, y0, x1, y1)

                    # ----------------------------------------------------------
                    # Shared text-cleaning helpers
                    # ----------------------------------------------------------
                    def clean_math_text(t: str) -> str:
                        cleaned = t.strip()
                        UNICODE_SUPERSCRIPTS = {
                            '⁰':'0','¹':'1','²':'2','³':'3','⁴':'4',
                            '⁵':'5','⁶':'6','⁷':'7','⁸':'8','⁹':'9',
                            '⁺':'+','⁻':'-','⁼':'=','⁽':'(','⁾':')',
                            'ⁿ':'n'
                        }
                        UNICODE_SUBSCRIPTS = {
                            '₀':'0','₁':'1','₂':'2','₃':'3','₄':'4',
                            '₅':'5','₆':'6','₇':'7','₈':'8','₉':'9',
                            '₊':'+','₋':'-','₌':'=','₍':'(','₎':')'
                        }
                        for char, val in UNICODE_SUPERSCRIPTS.items():
                            cleaned = cleaned.replace(char, f'^{val}')
                        for char, val in UNICODE_SUBSCRIPTS.items():
                            cleaned = cleaned.replace(char, f'_{val}')
                        cleaned = re.sub(r'\^([a-zA-Z0-9])(?![^{]*})', r'^{\1}', cleaned)
                        cleaned = re.sub(r'_([a-zA-Z0-9])(?![^{]*})', r'_{\1}', cleaned)
                        cleaned = re.sub(r'\b(sin|cos|tan|log|ln|lim|sqrt)\b', r'\\\1', cleaned)
                        cleaned = re.sub(r'\\sqrt\(([^)]+)\)', r'\\sqrt{\1}', cleaned)
                        cleaned = re.sub(r'\bd/d([xyt])\b', r'\\frac{d}{d\1}', cleaned)
                        # Add differential spacing for dx, dy, dt at the end or separated by space
                        cleaned = re.sub(r'\s+d([xyt])\b', r'\\,d\1', cleaned)
                        return cleaned

                    def parse_inline_fraction(text: str) -> str:
                        if '/' not in text:
                            return text
                        idx = text.find('/')
                        left_part = text[:idx].strip()
                        right_part = text[idx+1:].strip()
                        if left_part.endswith(')'):
                            depth = 0
                            left_start = -1
                            for i in range(len(left_part)-1, -1, -1):
                                if left_part[i] == ')':
                                    depth += 1
                                elif left_part[i] == '(':
                                    depth -= 1
                                    if depth == 0:
                                        left_start = i
                                        break
                            if left_start != -1:
                                num = left_part[left_start+1:-1]
                                prefix = left_part[:left_start]
                            else:
                                num = left_part
                                prefix = ""
                        else:
                            m = re.search(r'([a-zA-Z0-9^_+\-\s]+)$', left_part)
                            if m:
                                num = m.group(1).strip()
                                prefix = left_part[:m.start()]
                            else:
                                num = left_part
                                prefix = ""
                        if right_part.startswith('('):
                            depth = 0
                            right_end = -1
                            for i in range(len(right_part)):
                                if right_part[i] == '(':
                                    depth += 1
                                elif right_part[i] == ')':
                                    depth -= 1
                                    if depth == 0:
                                        right_end = i
                                        break
                            if right_end != -1:
                                den = right_part[1:right_end]
                                suffix = right_part[right_end+1:]
                            else:
                                den = right_part
                                suffix = ""
                        else:
                            m = re.match(r'^([a-zA-Z0-9^_+\-\s]+)', right_part)
                            if m:
                                den = m.group(1).strip()
                                suffix = right_part[m.end():]
                            else:
                                den = right_part
                                suffix = ""
                        return f"{prefix}\\frac{{{num.strip()}}}{{{den.strip()}}}{suffix}"

                    # ----------------------------------------------------------
                    # Process mathematical blocks via 2D Layout Math Parser
                    # ----------------------------------------------------------
                    reconstructed_blocks = []
                    for b in math_blocks:
                        if b.lines:
                            # ----------------------------------------------------------
                            # Parse 2D spatial layout tree from individual OCR component lines
                            # ----------------------------------------------------------
                            lines = b.lines
                            cleaned_lines = []
                            for line in lines:
                                txt = line.text.strip()
                                txt = re.sub(r'^Evaluate\s*:\s*', '', txt).strip()
                                if txt:
                                    cleaned_lines.append({
                                        "text": txt,
                                        "bbox": line.bbox,
                                        "confidence": line.confidence
                                    })
                            
                            if not cleaned_lines:
                                reconstructed_blocks.append(b)
                                continue
                                
                            # Helper for horizontal overlap
                            def get_overlap_x(box1, box2):
                                return max(0.0, min(box1[2], box2[2]) - max(box1[0], box2[0]))
                                
                            # 1. Detect fractions
                            fractions = []
                            used_indices = set()
                            for idx_i in range(len(cleaned_lines)):
                                if idx_i in used_indices:
                                    continue
                                for idx_j in range(len(cleaned_lines)):
                                    if idx_i == idx_j or idx_j in used_indices:
                                        continue
                                    b1 = cleaned_lines[idx_i]
                                    b2 = cleaned_lines[idx_j]
                                    
                                    overlap = get_overlap_x(b1["bbox"], b2["bbox"])
                                    w1 = b1["bbox"][2] - b1["bbox"][0]
                                    w2 = b2["bbox"][2] - b2["bbox"][0]
                                    min_w = min(w1, w2)
                                    
                                    if min_w > 0 and (overlap / min_w) > 0.5:
                                        y1_1 = b1["bbox"][3]
                                        y0_2 = b2["bbox"][1]
                                        y1_2 = b2["bbox"][3]
                                        y0_1 = b1["bbox"][1]
                                        
                                        if y1_1 <= y0_2 + 15:
                                            fractions.append((idx_i, idx_j))
                                            used_indices.add(idx_i)
                                            used_indices.add(idx_j)
                                            break
                                        elif y1_2 <= y0_1 + 15:
                                            fractions.append((idx_j, idx_i))
                                            used_indices.add(idx_i)
                                            used_indices.add(idx_j)
                                            break
                                            
                            other_lines = [cleaned_lines[i] for i in range(len(cleaned_lines)) if i not in used_indices]
                            
                            integral_box = None
                            differential_box = None
                            for line in other_lines:
                                txt = line["text"]
                                if any(sym in txt for sym in ["∫", "∮", "∬", "∭"]) or any(cmd in txt for cmd in ["\\int", "\\iint", "\\iiint", "\\oint"]):
                                    integral_box = line
                                elif txt.strip() in ["dx", "dy", "dt"] or re.match(r'^\\,?d[xyt]$', txt.strip()) or re.match(r'^d\s+[xyt]$', txt.strip()):
                                    differential_box = line
                                    
                            # Build semantic layout tree
                            fraction_nodes = []
                            for num_idx, den_idx in fractions:
                                num_line = cleaned_lines[num_idx]
                                den_line = cleaned_lines[den_idx]
                                num_txt = num_line["text"]
                                den_txt = den_line["text"]
                                fraction_nodes.append({
                                    "type": "Fraction",
                                    "numerator": {"type": "Numerator", "value": num_txt},
                                    "denominator": {"type": "Denominator", "value": den_txt},
                                    "bbox": (
                                        min(num_line["bbox"][0], den_line["bbox"][0]),
                                        min(num_line["bbox"][1], den_line["bbox"][1]),
                                        max(num_line["bbox"][2], den_line["bbox"][2]),
                                        max(num_line["bbox"][3], den_line["bbox"][3])
                                    )
                                })
                                
                            if integral_box:
                                tree_elements = []
                                for fn in fraction_nodes:
                                    tree_elements.append(fn)
                                for line in other_lines:
                                    if line == integral_box or line == differential_box:
                                        continue
                                    tree_elements.append({"type": "Expression", "value": line["text"]})
                                if differential_box:
                                    tree_elements.append({
                                        "type": "Differential",
                                        "value": differential_box["text"]
                                    })
                                math_tree = {
                                    "type": "Integral",
                                    "elements": tree_elements
                                }
                            else:
                                tree_elements = []
                                for fn in fraction_nodes:
                                    tree_elements.append(fn)
                                for line in other_lines:
                                    if line == differential_box:
                                        continue
                                    tree_elements.append({"type": "Expression", "value": line["text"]})
                                if differential_box:
                                    tree_elements.append({
                                        "type": "Differential",
                                        "value": differential_box["text"]
                                    })
                                if len(tree_elements) == 1:
                                    math_tree = tree_elements[0]
                                else:
                                    math_tree = {
                                        "type": "Expression",
                                        "elements": tree_elements
                                    }
                                    
                            # Recursive LaTeX generation
                            def to_latex(node: Dict[str, Any]) -> str:
                                ntype = node.get("type")
                                if ntype == "Integral":
                                    latex_parts = ["\\int"]
                                    for child in node.get("elements", []):
                                        latex_parts.append(to_latex(child))
                                    res = ""
                                    for idx, part in enumerate(latex_parts):
                                        if idx > 0 and latex_parts[idx].startswith("\\,d"):
                                            res += part
                                        else:
                                            if res:
                                                res += " " + part
                                            else:
                                                res = part
                                    return res
                                elif ntype == "Fraction":
                                    num_latex = to_latex(node["numerator"])
                                    den_latex = to_latex(node["denominator"])
                                    if num_latex.startswith('(') and num_latex.endswith(')'):
                                        num_latex = num_latex[1:-1]
                                    return f"\\frac{{{num_latex}}}{{{den_latex}}}"
                                elif ntype in ["Numerator", "Denominator", "Expression"]:
                                    if "elements" in node:
                                        latex_parts = []
                                        for child in node.get("elements", []):
                                            latex_parts.append(to_latex(child))
                                        res = ""
                                        for idx, part in enumerate(latex_parts):
                                            if idx > 0 and latex_parts[idx].startswith("\\,d"):
                                                res += part
                                            else:
                                                if res:
                                                    res += " " + part
                                                else:
                                                    res = part
                                        return res
                                    return clean_math_text(node.get("value", ""))
                                elif ntype == "Differential":
                                    val = clean_math_text(node.get("value", ""))
                                    m = re.search(r'd[xyt]$', val)
                                    if m:
                                        return f"\\,d{m.group(0)[1]}"
                                    else:
                                        return "\\,dx"
                                return ""
                                
                            latex_formula = to_latex(math_tree)
                            latex_formula = re.sub(r'\s+', ' ', latex_formula).strip()
                            
                            # Preserve original text representation
                            b.ocr_text = getattr(b, "ocr_text", None) or b.text
                            b.text = latex_formula
                            b.latex = latex_formula
                            b.block_type = "equation"
                            
                            # Build formatted semantic tree string for display
                            def format_tree_str(node, indent=0):
                                spacing = "    " * indent
                                lines = []
                                ntype = node.get("type")
                                if ntype == "Integral":
                                    lines.append(f"{spacing}Integral")
                                    for child in node.get("elements", []):
                                        lines.append(format_tree_str(child, indent + 1))
                                elif ntype == "Fraction":
                                    lines.append(f"{spacing}Fraction")
                                    lines.append(f"{spacing}    Numerator")
                                    lines.append(format_tree_str(node.get("numerator"), indent + 2))
                                    lines.append(f"{spacing}    Denominator")
                                    lines.append(format_tree_str(node.get("denominator"), indent + 2))
                                elif ntype == "Differential":
                                    lines.append(f"{spacing}Differential")
                                    lines.append(f"{spacing}    {node.get('value')}")
                                elif ntype in ["Numerator", "Denominator", "Expression"]:
                                    lines.append(f"{spacing}{node.get('value')}")
                                return "\n".join(lines)
                                
                            b.semantic_tree_str = format_tree_str(math_tree)
                            b.symbol_tree = math_tree
                            
                            if equation_model:
                                b.mathml = equation_model._generate_mathml(math_tree)
                                b.provenance = {
                                    "library": "PaddleOCR/MathReconstructor",
                                    "version": "1.0",
                                    "confidence": b.confidence,
                                    "fallback": False
                                }
                            reconstructed_blocks.append(b)
                        else:
                            # ----------------------------------------------------------
                            # Legacy fallback path
                            # ----------------------------------------------------------
                            raw = b.text.strip()
                            cleaned = clean_math_text(raw)
                            cleaned = cleaned.replace('∫', '\\int')
                            cleaned = cleaned.replace('∬', '\\iint')
                            cleaned = cleaned.replace('∭', '\\iiint')
                            
                            diff_match = re.search(r'\b(d[xyt])\s*$', cleaned)
                            if diff_match:
                                diff_token = diff_match.group(1)
                                body = cleaned[:diff_match.start()].strip()
                                if '/' in body:
                                    body = parse_inline_fraction(body)
                                latex_formula = f"{body} \\,{diff_token}"
                            else:
                                if '/' in cleaned:
                                    cleaned = parse_inline_fraction(cleaned)
                                latex_formula = cleaned
                                
                            latex_formula = re.sub(r'\s+', ' ', latex_formula).strip()
                            
                            b.text = latex_formula
                            b.latex = latex_formula
                            b.ocr_text = getattr(b, "ocr_text", None) or raw
                            b.block_type = "equation"
                            
                            if equation_model:
                                symbol_tree = equation_model._build_symbol_tree(latex_formula)
                                b.mathml = equation_model._generate_mathml(symbol_tree)
                                b.symbol_tree = symbol_tree
                                b.provenance = {
                                    "library": "PaddleOCR/MathReconstructor",
                                    "version": "1.0",
                                    "confidence": b.confidence,
                                    "fallback": False
                                }
                            reconstructed_blocks.append(b)
                            
                    blocks = non_math_blocks + reconstructed_blocks
                    page.statistics["blocks"] = sorted(blocks, key=lambda b: (b.bbox[1], b.bbox[0]))

                page.statistics["processing_time"] += (time.time() - start_time)
                continue
            
            for block in blocks:
                text = block.text
                is_math = False
                
                # Check if this block is contact info, metadata, page numbers, or footnotes
                is_contact = block.block_type in ["contact_info", "metadata", "page_number", "footnote"]
                has_email = bool(re.search(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', text))
                has_phone = bool(re.search(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', text))
                has_url = bool(re.search(r'https?://|www\.|github\.com|linkedin\.com', text, re.IGNORECASE))
                
                if is_contact or has_email or has_phone or has_url or "..." in text or " . . " in text:
                    is_math = False
                else:
                    clean_t = text.strip()
                    # Look for LaTeX expressions or math equations
                    # 1. Variables equal to numbers/expressions or simple algebraic patterns
                    has_variables = bool(re.search(r'\b[x-zX-Z]\b', clean_t)) or bool(re.search(r'\b[a-zA-Z]\b', clean_t))
                    has_operators = any(op in clean_t for op in ['+', '-', '*', '/', '^', '_', '=', '<', '>', '±', '×', '÷', '≈', '≠', '≤', '≥'])
                    has_parentheses = '(' in clean_t or ')' in clean_t or '[' in clean_t or ']' in clean_t
                    has_math_func = bool(re.search(r'\b(?:sin|cos|tan|log|ln|sqrt|exp|lim|arcsin|arccos|arctan)\b', clean_t))
                    has_calculus = bool(re.search(r'\b[dD]/d[xyt]\b', clean_t)) or bool(re.search(r'\bd[xyt]\b', clean_t)) or bool(re.search(r'd[xyt]$', clean_t))
                    has_math_symbols = any(sym in clean_t for sym in ["α", "β", "γ", "π", "Σ", "∫", "∬", "√", "λ", "θ", "∞", "∂", "∇", "Δ", "Ω", "μ", "σ", "φ", "ψ", "ω", "Π", "∝", "≡"])
                    has_latex = bool(re.search(r'\\[a-zA-Z]+', clean_t))
                    has_coeff = bool(re.search(r'\d+[a-zA-Z]', clean_t)) or bool(re.search(r'[a-zA-Z]\d+', clean_t))
                    
                    # Count normal English words
                    words = re.findall(r'\b[a-zA-Z]{4,}\b', clean_t)
                    words = [w for w in words if w.lower() not in ["sin", "cos", "tan", "log", "sqrt", "lim", "exp", "delta", "beta", "alpha", "gamma", "theta"]]
                    
                    # If word count is low, it is highly likely to be math if any operator or variable is present
                    if len(words) <= 3:
                        if has_operators or has_parentheses or has_math_func or has_calculus or has_math_symbols or has_latex or has_coeff or '^' in clean_t or '_' in clean_t:
                            is_math = True
                    else:
                        # Even if word count is higher, explicit math symbols or equations qualify
                        if has_math_symbols or has_calculus or has_latex or re.search(r'\b[a-zA-Z]\s*=\s*', clean_t) or "^" in clean_t:
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
                        block.confidence = prov.get("confidence", 0.95)
                        
            page.statistics["processing_time"] += (time.time() - start_time)
            
        return doc_graph
