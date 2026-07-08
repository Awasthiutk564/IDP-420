import os
import json
import shutil
from typing import List, Dict, Any
from .stage import Stage
from utils.document_graph import DocumentNode

class StageOutput(Stage):
    def __init__(self):
        super().__init__(name="Export Engine")

    def run(self, doc_graph: DocumentNode, pdf_path: str, adapters: List[Any], classifiers: Dict[str, Any], models: Dict[str, Any]) -> DocumentNode:
        output_dir = os.path.join("data", "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # 1. JSON Export
        json_path = os.path.join(output_dir, "hybrid_hierarchy.json")
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(doc_graph.to_dict(), jf, indent=2, default=str, ensure_ascii=False)
            
        # 2. Markdown Export
        md_path = os.path.join(output_dir, "hybrid_hierarchy.md")
        with open(md_path, "w", encoding="utf-8") as mf:
            mf.write(f"# Document: {doc_graph.filename}\n")
            mf.write(f"Type: {doc_graph.document_type}\n\n")
            
            for page in doc_graph.pages:
                mf.write(f"## Page {page.page_number}\n")
                blocks = page.statistics.get("blocks", [])
                for b in blocks:
                    if b.block_type == "title":
                        mf.write(f"# {b.text}\n\n")
                    elif b.block_type == "heading_1":
                        mf.write(f"## {b.text}\n\n")
                    elif b.block_type == "heading_2":
                        mf.write(f"### {b.text}\n\n")
                    elif b.block_type == "paragraph":
                        mf.write(f"{b.text}\n\n")
                    elif b.block_type == "equation":
                        mf.write(f"$$\n{b.latex}\n$$\n\n")
                    elif b.block_type == "table":
                        mf.write(f"```\n{b.text}\n```\n\n")
                        
        # 3. HTML Export (with MathML rendering inline)
        html_path = os.path.join(output_dir, "hybrid_hierarchy.html")
        with open(html_path, "w", encoding="utf-8") as hf:
            hf.write("<!DOCTYPE html>\n<html>\n<head>\n")
            hf.write("<script type='text/javascript' async src='https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/MathJax.js?config=MML_HTMLorMML'></script>\n")
            hf.write(f"<title>{doc_graph.filename}</title>\n</head>\n<body>\n")
            for page in doc_graph.pages:
                blocks = page.statistics.get("blocks", [])
                for b in blocks:
                    if b.block_type == "title":
                        hf.write(f"<h1>{b.text}</h1>\n")
                    elif b.block_type == "heading_1":
                        hf.write(f"<h2>{b.text}</h2>\n")
                    elif b.block_type == "heading_2":
                        hf.write(f"<h3>{b.text}</h3>\n")
                    elif b.block_type == "paragraph":
                        hf.write(f"<p>{b.text}</p>\n")
                    elif b.block_type == "equation":
                        # Render MathML directly
                        if b.mathml:
                            hf.write(f"<div class='equation'>{b.mathml}</div>\n")
                        else:
                            hf.write(f"<div class='equation'>$${b.latex}$$</div>\n")
            hf.write("</body>\n</html>\n")

        # 4. XML Export
        xml_path = os.path.join(output_dir, "hybrid_hierarchy.xml")
        with open(xml_path, "w", encoding="utf-8") as xf:
            xf.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            xf.write(f'<document filename="{doc_graph.filename}" type="{doc_graph.document_type}">\n')
            for page in doc_graph.pages:
                xf.write(f'  <page number="{page.page_number}">\n')
                blocks = page.statistics.get("blocks", [])
                for b in blocks:
                    xf.write(f'    <block type="{b.block_type}">\n')
                    xf.write(f'      <text><![CDATA[{b.text}]]></text>\n')
                    if b.latex:
                        xf.write(f'      <latex><![CDATA[{b.latex}]]></latex>\n')
                    xf.write('    </block>\n')
                xf.write('  </page>\n')
            xf.write('</document>\n')

        # 5. LaTeX Export
        tex_path = os.path.join(output_dir, "hybrid_hierarchy.tex")
        with open(tex_path, "w", encoding="utf-8") as tf:
            tf.write("\\documentclass{article}\n\\usepackage{amsmath}\n\\begin{document}\n")
            for page in doc_graph.pages:
                blocks = page.statistics.get("blocks", [])
                for b in blocks:
                    if b.block_type == "title":
                        tf.write(f"\\title{{{b.text}}}\n\\maketitle\n")
                    elif b.block_type == "heading_1":
                        tf.write(f"\\section{{{b.text}}}\n")
                    elif b.block_type == "heading_2":
                        tf.write(f"\\subsection{{{b.text}}}\n")
                    elif b.block_type == "paragraph":
                        # Escape special characters
                        escaped = b.text.replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")
                        tf.write(f"{escaped}\n\n")
                    elif b.block_type == "equation":
                        tf.write(f"\\begin{{equation}}\n{b.latex}\n\\end{{equation}}\n\n")
            tf.write("\\end{document}\n")
            
        # Clean up incremental temp directory
        temp_dir = os.path.join("data", "output", "temp_pages")
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
                
        return doc_graph
