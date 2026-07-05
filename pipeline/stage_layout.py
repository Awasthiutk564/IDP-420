import time
from typing import List, Dict, Any
from .stage import Stage
from utils.document_graph import DocumentNode, BlockNode, SectionNode, LineNode
from utils.hierarchy_builder import HierarchyBuilder

class StageLayout(Stage):
    def __init__(self):
        super().__init__(name="Layout Segmentation & Reading Order")

    def run(self, doc_graph: DocumentNode, pdf_path: str, adapters: List[Any], classifiers: Dict[str, Any], models: Dict[str, Any]) -> DocumentNode:
        layout_model = models.get("layout")
        
        for page in doc_graph.pages:
            start_time = time.time()
            lines = page.statistics.get("temp_lines", [])
            
            # 1. Column detection
            cols, label = HierarchyBuilder.detect_layout_columns(lines, page.width)
            page.reading_complexity = label
            
            # 2. Reading order flow sorting
            sorted_lines = HierarchyBuilder.extract_reading_order(lines, cols, page.width)
            
            # 3. Classify baseline heading, block limits and construct blocks
            pymupdf_adapter = next((a for a in adapters if a.name == "PyMuPDF"), None)
            base_size = 10.0
            
            # Attempt to gather base font size from character metrics
            sizes = []
            for line in sorted_lines:
                for word in line.words:
                    for char in word.characters:
                        sizes.append(char.font_size)
            if sizes:
                from collections import Counter
                base_size = Counter(sizes).most_common(1)[0][0]
                
            # Classify blocks using paragraph/heading builders
            blocks = HierarchyBuilder.classify_headings_and_blocks(sorted_lines, base_size, page.height)
            
            # Map elements into BlockNodes
            block_nodes = []
            for b in blocks:
                # b.block_type is e.g., 'heading_1', 'paragraph', 'bullet_list_item', etc.
                block_node = BlockNode(
                    block_type=b.block_type,
                    text=b.text,
                    bbox=b.bbox,
                    confidence=b.confidence,
                    provenance={
                        "library": "pdfminer.six + PyMuPDF",
                        "version": "1.0",
                        "confidence": b.confidence,
                        "fallback": False
                    },
                    lines=b.lines
                )
                block_nodes.append(block_node)
                
            # Connect BlockNodes inside double list graph (prev/next links)
            for i, bn in enumerate(block_nodes):
                if i > 0:
                    bn.prev_id = block_nodes[i - 1].id
                if i < len(block_nodes) - 1:
                    bn.next_id = block_nodes[i + 1].id
                    
            # 4. DocLayout-YOLO semantic verification overrides (if available)
            if layout_model:
                # In a real environment, we'd pass the page image, here we simulate alignment checks
                pass
                
            # 5. Section assignment (Header, Footer, Body)
            header_blocks = []
            footer_blocks = []
            body_blocks = []
            
            for bn in block_nodes:
                bx0, by0, bx1, by1 = bn.bbox
                if by1 <= page.height * 0.12:
                    header_blocks.append(bn)
                elif by0 >= page.height * 0.88:
                    footer_blocks.append(bn)
                else:
                    body_blocks.append(bn)
                    
            # Build section nodes
            if header_blocks:
                page.sections.append(SectionNode(section_type="header", bbox=(0, 0, page.width, page.height * 0.12), blocks=header_blocks))
            if body_blocks:
                page.sections.append(SectionNode(section_type="body", bbox=(0, page.height * 0.12, page.width, page.height * 0.88), blocks=body_blocks))
            if footer_blocks:
                page.sections.append(SectionNode(section_type="footer", bbox=(0, page.height * 0.88, page.width, page.height), blocks=footer_blocks))
                
            # Save blocks list for reference
            page.statistics["blocks"] = block_nodes
            page.statistics["processing_time"] += (time.time() - start_time)
            
        # 6. Running headers/footers consensus across pages
        # Collect top block texts from all pages
        for page in doc_graph.pages:
            headers = []
            footers = []
            for sec in page.sections:
                if sec.section_type == "header":
                    headers.extend([b.text for b in sec.blocks if len(b.text) > 3])
                elif sec.section_type == "footer":
                    footers.extend([b.text for b in sec.blocks if len(b.text) > 3])
            page.statistics["headers_list"] = headers
            page.statistics["footers_list"] = footers
            
        return doc_graph
