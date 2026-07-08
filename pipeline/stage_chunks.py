import time
import re
from typing import List, Dict, Any
from .stage import Stage
from utils.document_graph import DocumentNode

class StageChunks(Stage):
    def __init__(self):
        super().__init__(name="Semantic Chunking & Knowledge Graph Builder")

    def run(self, doc_graph: DocumentNode, pdf_path: str, adapters: List[Any], classifiers: Dict[str, Any], models: Dict[str, Any]) -> DocumentNode:
        start_time = time.time()
        
        # 1. Build Semantic Chunks (RAG ready)
        chunks = []
        entities = set()
        relationships = []
        
        current_heading = "Main Header"
        
        for page in doc_graph.pages:
            blocks = page.statistics.get("blocks", [])
            for block in blocks:
                if block.block_type.startswith("heading"):
                    current_heading = block.text
                elif block.block_type == "paragraph":
                    # Create semantic chunk
                    chunk_id = f"chunk_{len(chunks) + 1}"
                    chunk_data = {
                        "id": chunk_id,
                        "text": block.text,
                        "page": page.page_number,
                        "bbox": block.bbox,
                        "heading": current_heading,
                        "references": block.references,
                        "contains_equations": block.contains_equations,
                        # Simulated embedding vector (length 32 for testing)
                        "embedding": [round(0.01 * (i + len(block.text)), 4) for i in range(32)]
                    }
                    chunks.append(chunk_data)
                    
                    # Extract entities from paragraph text (simple capitalized word heuristics)
                    words = re.findall(r'\b[A-Z][a-zA-Z0-9\-\.]+\b', block.text)
                    for w in words:
                        if len(w) > 3 and w.lower() not in ["page", "table", "figure"]:
                            entities.add(w)
                            
        # Map entities into Knowledge Graph Node list
        doc_graph.chunks = chunks
        
        entity_nodes = []
        for idx, ent in enumerate(sorted(entities)):
            ent_id = f"ent_{idx+1}"
            entity_nodes.append({
                "id": ent_id,
                "label": ent,
                "type": "Technology/Term" if "." in ent or "PDF" in ent else "Entity"
            })
            
        # Build relationships between entities appearing in the same chunks
        for chunk in chunks:
            chunk_entities = [e for e in entity_nodes if e["label"] in chunk["text"]]
            if len(chunk_entities) >= 2:
                for i in range(len(chunk_entities) - 1):
                    relationships.append({
                        "source": chunk_entities[i]["id"],
                        "target": chunk_entities[i+1]["id"],
                        "relation": "co-occurs",
                        "context": f"Page {chunk['page']}: {chunk['heading']}"
                    })
                    
        doc_graph.knowledge_graph["entities"] = entity_nodes
        doc_graph.knowledge_graph["relationships"] = relationships
        
        return doc_graph
