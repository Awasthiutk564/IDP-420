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
                
                # Image statistics breakdown (Issue 9)
                img_stats = page.statistics.get("image_counts", {})
                if img_stats:
                    mf.write("### Visual Statistics\n")
                    mf.write(f"- Tables: {len(page.tables)}\n")
                    mf.write(f"- Logos: {img_stats.get('logos', 0)}\n")
                    mf.write(f"- Figures: {img_stats.get('figures', 0)}\n")
                    mf.write(f"- Charts: {img_stats.get('charts', 0)}\n")
                    mf.write(f"- Icons: {img_stats.get('icons', 0)}\n")
                    mf.write(f"- Photos: {img_stats.get('photos', 0)}\n")
                    mf.write(f"- Diagrams: {img_stats.get('diagrams', 0)}\n\n")
                    
                blocks = page.statistics.get("blocks", [])
                for b in blocks:
                    if b.block_type == "title":
                        mf.write(f"# {b.text}\n\n")
                    elif b.block_type == "heading_1":
                        mf.write(f"## {b.text}\n\n")
                    elif b.block_type == "heading_2":
                        mf.write(f"### {b.text}\n\n")
                    elif b.block_type == "heading_3":
                        mf.write(f"#### {b.text}\n\n")
                    elif b.block_type in ["paragraph", "contact_info", "metadata"]:
                        mf.write(f"{b.text}\n\n")
                    elif b.block_type in ["list_item", "project_item"]:
                        mf.write(f"* {b.text}\n\n")
                    elif b.block_type in ["logo", "icon", "diagram", "chart", "photo", "figure"]:
                        mf.write(f"![{b.block_type.capitalize()}]({b.latex or ''}) - {b.text}\n\n")
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
                hf.write(f"<hr><h2>Page {page.page_number}</h2>\n")
                
                # Visual statistics breakdown (Issue 9)
                img_stats = page.statistics.get("image_counts", {})
                if img_stats:
                    hf.write("<div class='visual-statistics'>\n")
                    hf.write("<h4>Estimated Visual Statistics:</h4>\n")
                    hf.write("<ul>\n")
                    hf.write(f"  <li>Tables: {len(page.tables)}</li>\n")
                    hf.write(f"  <li>Logos: {img_stats.get('logos', 0)}</li>\n")
                    hf.write(f"  <li>Figures: {img_stats.get('figures', 0)}</li>\n")
                    hf.write(f"  <li>Charts: {img_stats.get('charts', 0)}</li>\n")
                    hf.write(f"  <li>Icons: {img_stats.get('icons', 0)}</li>\n")
                    hf.write(f"  <li>Photos: {img_stats.get('photos', 0)}</li>\n")
                    hf.write(f"  <li>Diagrams: {img_stats.get('diagrams', 0)}</li>\n")
                    hf.write("</ul>\n</div>\n")
                    
                blocks = page.statistics.get("blocks", [])
                for b in blocks:
                    if b.block_type == "title":
                        hf.write(f"<h1>{b.text}</h1>\n")
                    elif b.block_type == "heading_1":
                        hf.write(f"<h2>{b.text}</h2>\n")
                    elif b.block_type == "heading_2":
                        hf.write(f"<h3>{b.text}</h3>\n")
                    elif b.block_type == "heading_3":
                        hf.write(f"<h4>{b.text}</h4>\n")
                    elif b.block_type in ["paragraph", "metadata"]:
                        hf.write(f"<p>{b.text}</p>\n")
                    elif b.block_type == "contact_info":
                        hf.write(f"<div class='contact-info' style='background:#f4f4f4;padding:5px;'><p>{b.text}</p></div>\n")
                    elif b.block_type in ["list_item", "project_item"]:
                        hf.write(f"<li>{b.text}</li>\n")
                    elif b.block_type in ["logo", "icon", "diagram", "chart", "photo", "figure"]:
                        hf.write(f"<div class='visual-block' style='border:1px solid #ccc;padding:10px;margin:5px;'><strong>{b.block_type.upper()}:</strong> {b.text}</div>\n")
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
                
                # XML Image statistics (Issue 9)
                img_stats = page.statistics.get("image_counts", {})
                if img_stats:
                    xf.write('    <image_statistics>\n')
                    xf.write(f'      <tables>{len(page.tables)}</tables>\n')
                    xf.write(f'      <logos>{img_stats.get("logos", 0)}</logos>\n')
                    xf.write(f'      <figures>{img_stats.get("figures", 0)}</figures>\n')
                    xf.write(f'      <charts>{img_stats.get("charts", 0)}</charts>\n')
                    xf.write(f'      <icons>{img_stats.get("icons", 0)}</icons>\n')
                    xf.write(f'      <photos>{img_stats.get("photos", 0)}</photos>\n')
                    xf.write(f'      <diagrams>{img_stats.get("diagrams", 0)}</diagrams>\n')
                    xf.write('    </image_statistics>\n')
                    
                blocks = page.statistics.get("blocks", [])
                for b in blocks:
                    parent_attr = f' parent="{b.parent_id}"' if getattr(b, 'parent_id', None) else ""
                    xf.write(f'    <block type="{b.block_type}"{parent_attr}>\n')
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
                
                # LaTeX Image statistics (Issue 9)
                img_stats = page.statistics.get("image_counts", {})
                if img_stats:
                    tf.write("\\subsubsection*{Estimated Page Visual Statistics}\n")
                    tf.write("\\begin{itemize}\n")
                    tf.write(f"  \\item Tables: {len(page.tables)}\n")
                    tf.write(f"  \\item Logos: {img_stats.get('logos', 0)}\n")
                    tf.write(f"  \\item Figures: {img_stats.get('figures', 0)}\n")
                    tf.write(f"  \\item Charts: {img_stats.get('charts', 0)}\n")
                    tf.write(f"  \\item Icons: {img_stats.get('icons', 0)}\n")
                    tf.write(f"  \\item Photos: {img_stats.get('photos', 0)}\n")
                    tf.write(f"  \\item Diagrams: {img_stats.get('diagrams', 0)}\n")
                    tf.write("\\end{itemize}\n\n")
                    
                blocks = page.statistics.get("blocks", [])
                for b in blocks:
                    if b.block_type == "title":
                        tf.write(f"\\title{{{b.text}}}\n\\maketitle\n")
                    elif b.block_type == "heading_1":
                        tf.write(f"\\section{{{b.text}}}\n")
                    elif b.block_type == "heading_2":
                        tf.write(f"\\subsection{{{b.text}}}\n")
                    elif b.block_type == "heading_3":
                        tf.write(f"\\subsubsection{{{b.text}}}\n")
                    elif b.block_type in ["paragraph", "metadata"]:
                        # Escape special characters
                        escaped = b.text.replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")
                        tf.write(f"{escaped}\n\n")
                    elif b.block_type == "contact_info":
                        escaped = b.text.replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")
                        tf.write(f"\\texttt{{{escaped}}}\n\n")
                    elif b.block_type in ["list_item", "project_item"]:
                        escaped = b.text.replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")
                        tf.write(f"\\textbullet\\ {escaped}\n\n")
                    elif b.block_type in ["logo", "icon", "diagram", "chart", "photo", "figure"]:
                        escaped = b.text.replace("_", "\\_").replace("&", "\\&").replace("%", "\\%")
                        tf.write(f"\\begin{{figure}}[h]\n\\centering\n% Visual resource: {b.latex or ''}\n\\caption{{{escaped}}}\n\\end{{figure}}\n\n")
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
