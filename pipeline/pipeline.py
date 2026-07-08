import os
import json
import time
from typing import List, Dict, Any
from utils.document_graph import DocumentNode

class Pipeline:
    def __init__(self, stages: List[Any], adapters: List[Any], classifiers: Dict[str, Any], models: Dict[str, Any]):
        self.stages = stages
        self.adapters = adapters
        self.classifiers = classifiers
        self.models = models
        self.temp_dir = os.path.join("data", "output", "temp_pages")

    def execute(self, pdf_path: str, filename: str) -> DocumentNode:
        # Create temp folder for incremental backup
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Initialize graph node
        doc_graph = DocumentNode(filename=filename, metadata={})
        
        # Execute each stage
        for stage in self.stages:
            start_time = time.time()
            # print(f"Executing stage: {stage.name}...")
            doc_graph = stage.run(
                doc_graph=doc_graph, 
                pdf_path=pdf_path, 
                adapters=self.adapters, 
                classifiers=self.classifiers, 
                models=self.models
            )
            # Incremental Page Save backup simulation
            self._incremental_save(doc_graph)
            
        return doc_graph

    def _incremental_save(self, doc_graph: DocumentNode):
        """
        Incrementally saves intermediate state to disk page-by-page.
        Enables recovery in case of system failures.
        """
        for page in doc_graph.pages:
            page_file = os.path.join(self.temp_dir, f"page_{page.page_number}.json")
            try:
                with open(page_file, "w", encoding="utf-8") as pf:
                    json.dump(page.to_dict(), pf, indent=2, default=str)
            except Exception:
                pass
