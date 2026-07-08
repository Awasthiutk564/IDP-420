import time
from typing import List, Dict, Any
from .stage import Stage
from utils.document_graph import DocumentNode

class StageTables(Stage):
    def __init__(self):
        super().__init__(name="Table Extraction & Consensus Voting")

    def run(self, doc_graph: DocumentNode, pdf_path: str, adapters: List[Any], classifiers: Dict[str, Any], models: Dict[str, Any]) -> DocumentNode:
        plumber_adapter = next((a for a in adapters if a.name == "pdfplumber"), None)
        table_model = models.get("table")
        
        plumber_pages = plumber_adapter.extract_pages_raw(pdf_path) if plumber_adapter else []
        
        for idx, page in enumerate(doc_graph.pages):
            start_time = time.time()
            p_data = plumber_pages[idx] if idx < len(plumber_pages) else {}
            
            raw_tables = p_data.get("tables", [])
            
            # Execute table voting engine (integrates Table Transformer & pdfplumber consensus)
            voted_tables = []
            provenance_metrics = {
                "library": "pdfplumber",
                "version": "0.9.0",
                "confidence": 0.90,
                "fallback": False
            }
            
            if table_model and raw_tables:
                voted_tables, provenance_metrics = table_model.run(raw_tables)
            else:
                for tbl in raw_tables:
                    voted_tables.append({
                        "bbox": tbl["bbox"],
                        "rows": tbl["rows"],
                        "columns": tbl["columns"],
                        "confidence": 0.90,
                        "cells": tbl.get("cells", [])
                    })
                    
            page.tables = voted_tables
            
            # Link table bounding boxes with table layout categories inside page.statistics["blocks"]
            blocks = page.statistics.get("blocks", [])
            for tbl in page.tables:
                # Add table block representation
                from utils.document_graph import BlockNode
                tbl_block = BlockNode(
                    block_type="table",
                    text=f"Table ({tbl['rows']} rows x {tbl['columns']} cols)",
                    bbox=tbl["bbox"],
                    confidence=tbl["confidence"],
                    provenance=provenance_metrics,
                    lines=[]
                )
                # Map cell values to text representation
                tbl_text = []
                for row in tbl.get("cells", []):
                    if row:
                        tbl_text.append(" | ".join(str(cell or "") for cell in row))
                if tbl_text:
                    tbl_block.text += "\n" + "\n".join(tbl_text)
                    
                blocks.append(tbl_block)
                
            page.statistics["processing_time"] += (time.time() - start_time)
            
        return doc_graph
