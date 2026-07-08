"""
Math Normalizer Utility
-----------------------

Normalizes raw text extracted from OCR or digital PDFs that contains
mathematical expressions, converting common OCR artifacts, Unicode
symbols, and notational patterns into clean, parseable math strings.

Examples of what this normalizes:
  - "x2"  (OCR missing caret)   -> "x^2"
  - "x2"  (Unicode superscript) -> "x^2"
  - "sqrt(x)"                   -> "\\sqrt{x}"
  - "2x3"  (Unicode multiply)   -> "2*3"
  - "E=mc^2"                    -> proper LaTeX via sympy
"""

import re
from typing import Optional


# ---------------------------------------------------------------------------
# Unicode superscript -> ASCII digit map
# ---------------------------------------------------------------------------
_SUPERSCRIPT_MAP = {
    "\u2070": "0", "\u00b9": "1", "\u00b2": "2", "\u00b3": "3", "\u2074": "4",
    "\u2075": "5", "\u2076": "6", "\u2077": "7", "\u2078": "8", "\u2079": "9",
    "\u207a": "+", "\u207b": "-", "\u207f": "n",
}

# Unicode subscript -> ASCII digit map
_SUBSCRIPT_MAP = {
    "\u2080": "0", "\u2081": "1", "\u2082": "2", "\u2083": "3", "\u2084": "4",
    "\u2085": "5", "\u2086": "6", "\u2087": "7", "\u2088": "8", "\u2089": "9",
    "\u208a": "+", "\u208b": "-", "\u2099": "n", "\u2090": "a", "\u2093": "x",
}

# Greek letters -> LaTeX commands
_GREEK_MAP = {
    "\u03b1": r"\alpha",   "\u03b2": r"\beta",    "\u03b3": r"\gamma",   "\u03b4": r"\delta",
    "\u03b5": r"\epsilon", "\u03b6": r"\zeta",    "\u03b7": r"\eta",     "\u03b8": r"\theta",
    "\u03b9": r"\iota",    "\u03ba": r"\kappa",   "\u03bb": r"\lambda",  "\u03bc": r"\mu",
    "\u03bd": r"\nu",      "\u03be": r"\xi",      "\u03c0": r"\pi",      "\u03c1": r"\rho",
    "\u03c3": r"\sigma",   "\u03c4": r"\tau",     "\u03c5": r"\upsilon",  "\u03c6": r"\phi",
    "\u03c7": r"\chi",     "\u03c8": r"\psi",     "\u03c9": r"\omega",
    "\u0393": r"\Gamma",   "\u0394": r"\Delta",   "\u0398": r"\Theta",
    "\u039b": r"\Lambda",  "\u039e": r"\Xi",      "\u03a0": r"\Pi",      "\u03a3": r"\Sigma",
    "\u03a5": r"\Upsilon",  "\u03a6": r"\Phi",    "\u03a8": r"\Psi",     "\u03a9": r"\Omega",
}

# Common math operator Unicode -> ASCII/LaTeX
_OPERATOR_MAP = {
    "\u00d7": "*",            "\u00f7": "/",          "\u00b1": r"\pm",
    "\u2213": r"\mp",         "\u2248": r"\approx",   "\u2260": r"\neq",
    "\u2264": r"\leq",        "\u2265": r"\geq",      "\u2261": r"\equiv",
    "\u221d": r"\propto",     "\u221e": r"\infty",
    "\u2192": r"\rightarrow", "\u2190": r"\leftarrow", "\u2194": r"\leftrightarrow",
    "\u21d2": r"\Rightarrow", "\u21d4": r"\Leftrightarrow",
    "\u2208": r"\in",         "\u2209": r"\notin",    "\u2282": r"\subset",
    "\u2286": r"\subseteq",   "\u222a": r"\cup",      "\u2229": r"\cap",
    "\u2205": r"\emptyset",   "\u2202": r"\partial",  "\u2207": r"\nabla",
    "\u2211": r"\sum",        "\u220f": r"\prod",     "\u222b": r"\int",
    "\u222c": r"\iint",       "\u221a": r"\sqrt",
    "\u00b7": r"\cdot",       "\u2297": r"\otimes",   "\u2295": r"\oplus",
}


def normalize_math_text(text: str) -> str:
    """
    Full pipeline: normalize OCR/PDF math text to a clean ASCII/LaTeX string.

    Steps applied:
    1. Strip surrounding whitespace and dollar-sign wrappers.
    2. Map Unicode superscript digits -> ^digit
    3. Map Unicode subscript digits -> _digit
    4. Map Greek letters -> LaTeX commands
    5. Map math operator symbols -> LaTeX commands
    6. Fix common OCR artifacts (e.g. missing ^ before digit after variable letter)
    7. Convert Python-style ** power to LaTeX ^
    8. Fix sqrt notation
    9. Normalize whitespace.

    Returns the normalized math string.
    """
    if not text:
        return text

    t = text.strip()

    # Remove dollar signs / LaTeX wrappers if already present
    t = re.sub(r'^\$+|\$+$', '', t).strip()
    t = re.sub(r'^\\?\[|\\?\]$', '', t).strip()

    # 1. Unicode superscripts -> ^digit
    for char, digit in _SUPERSCRIPT_MAP.items():
        t = t.replace(char, f"^{digit}")

    # 2. Unicode subscripts -> _digit
    for char, digit in _SUBSCRIPT_MAP.items():
        t = t.replace(char, f"_{digit}")

    # 3. Greek letters -> LaTeX
    for char, latex_cmd in _GREEK_MAP.items():
        t = t.replace(char, latex_cmd)

    # 4. Math operators -> LaTeX
    for char, latex_cmd in _OPERATOR_MAP.items():
        t = t.replace(char, latex_cmd)

    # 5. OCR artifact: single variable letter immediately followed by a bare digit
    #    e.g. "x2" -> "x^2", "a3" -> "a^3"
    #    Avoid replacing in "sin30", "log10", "cm2" (unit abbreviations)
    t = re.sub(
        r'(?<![a-zA-Z\\])([a-zA-Z])([2-9])\b(?!\^)',
        lambda m: f"{m.group(1)}^{m.group(2)}",
        t
    )

    # 6. Convert Python-style power (**) to LaTeX (^)
    t = t.replace("**", "^")

    # 7. Fix sqrt: "sqrt x" or "sqrt(x)" -> "\sqrt{x}"
    t = re.sub(r'(?<!\\)sqrt\s*\(([^)]+)\)', r'\\sqrt{\1}', t)
    t = re.sub(r'(?<!\\)sqrt\s+([a-zA-Z0-9]+)', r'\\sqrt{\1}', t)

    # 8. Clean up dangling ^ or _ spacing
    t = re.sub(r'\^\s+', '^', t)
    t = re.sub(r'_\s+', '_', t)

    # 9. Normalize consecutive spaces
    t = re.sub(r'  +', ' ', t).strip()

    return t


def is_likely_math(text: str) -> bool:
    """
    Returns True if the given text snippet is likely to be a mathematical
    expression or equation.
    """
    if not text or len(text.strip()) < 2:
        return False

    stripped = text.strip()

    # Exclude table of contents lines with leader dots
    if re.search(r'\.{3,}', stripped) or re.search(r'( \. ){2,}', stripped):
        return False

    signals = [
        # LaTeX commands already present
        bool(re.search(
            r'\\(?:frac|sqrt|sum|int|prod|alpha|beta|gamma|delta|pi|sigma|'
            r'theta|lambda|phi|psi|omega|sin|cos|tan|log|ln|lim|partial|'
            r'nabla|infty|pm|times|div)\b', text)),
        # Power/superscript notation
        bool(re.search(r'[a-zA-Z0-9]\^[a-zA-Z0-9{]', text)),
        # Subscript notation
        bool(re.search(r'[a-zA-Z0-9]_[a-zA-Z0-9{]', text)),
        # Greek/math Unicode symbols
        bool(any(c in text for c in
                 "\u03b1\u03b2\u03b3\u03b4\u03b5\u03b6\u03b7\u03b8"
                 "\u03b9\u03ba\u03bb\u03bc\u03bd\u03be\u03c0\u03c1"
                 "\u03c3\u03c4\u03c5\u03c6\u03c7\u03c8\u03c9"
                 "\u0393\u0394\u0398\u039b\u039e\u03a0\u03a3\u03a5\u03a6\u03a8\u03a9"
                 "\u222b\u2211\u221a\u00b1\u00d7\u00f7\u2260\u2264\u2265\u2248\u221e\u2202\u2207")),
        # Simple algebraic: variable = expression (short words only)
        bool(re.search(r'\b[a-zA-Z]\s*=\s*[-+]?\d', text) and
             not re.search(r'\b[a-zA-Z]{4,}\s*=', text)),
        # f(x) style function definitions
        bool(re.search(r'\b[a-zA-Z]\([a-zA-Z]\)\s*=', text)),
        # Python-style power
        bool(re.search(r'[a-zA-Z0-9]\*\*[a-zA-Z0-9]', text)),
        # Unicode superscripts
        bool(any(c in text for c in "\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u2070\u00b9")),
    ]

    return any(signals)


def extract_latex_from_sympy(expr_text: str) -> Optional[str]:
    """
    Attempt to parse the expression using sympy and return its LaTeX form.
    Falls back to None if parsing fails.
    """
    try:
        from sympy import latex
        from sympy.parsing.sympy_parser import (
            parse_expr,
            standard_transformations,
            implicit_multiplication_application,
            convert_xor,
        )

        transformations = standard_transformations + (
            implicit_multiplication_application,
            convert_xor,  # converts x^2 -> x**2 for sympy
        )

        # Skip if already has LaTeX commands (don't double-convert)
        if "\\" in expr_text and any(
            cmd in expr_text for cmd in [r"\sum", r"\int", r"\frac", r"\alpha", r"\pi"]
        ):
            return None

        # Handle equations with "=" sign
        if "=" in expr_text and not any(c in expr_text for c in ["==", "<=", ">="]):
            parts = expr_text.split("=", 1)
            lhs_text = parts[0].strip()
            rhs_text = parts[1].strip()
            # Skip if either side has LaTeX commands
            if "\\" in lhs_text or "\\" in rhs_text:
                return None
            try:
                lhs = parse_expr(lhs_text, transformations=transformations)
                rhs = parse_expr(rhs_text, transformations=transformations)
                return f"{latex(lhs)} = {latex(rhs)}"
            except Exception:
                return None
        else:
            if "\\" in expr_text:
                return None  # Already has LaTeX commands
            expr = parse_expr(expr_text, transformations=transformations)
            return latex(expr)

    except Exception:
        return None


def full_math_to_latex(raw_text: str) -> str:
    """
    Master function: takes raw text (OCR or PDF), normalizes it, then tries
    sympy-based LaTeX conversion, falling back to the normalized text.

    Returns the best available LaTeX representation.
    """
    # Step 1: Normalize Unicode and OCR artifacts
    normalized = normalize_math_text(raw_text)

    # Step 2: Try sympy conversion (most accurate)
    sympy_latex = extract_latex_from_sympy(normalized)
    if sympy_latex:
        return sympy_latex

    # Step 3: Fallback to normalized text (still much better than raw OCR)
    return normalized
