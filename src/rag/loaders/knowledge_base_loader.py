import os
from typing import List
from src.rag.loaders.documents import Document
from src.rag.loaders.json_loader import JSONLoader
from src.rag.loaders.markdown_loader import MarkdownLoader
from src.rag.loaders.pdf_loader import PDFLoader
from src.utils.logger import custom_logger as logger

class KnowledgeBaseLoader:
    """
    Unified directory scanner that recursively walks the raw data folder and routes
    each file to its appropriate loader (JSON, Markdown, PDF) based on extension.
    """
    def __init__(self, directory_path: str):
        self.directory_path = directory_path

    def load_all(self) -> List[Document]:
        """
        Recursively scans the directory and returns a consolidated list of all parsed Document objects.
        """
        if not os.path.exists(self.directory_path):
            logger.error(f"Knowledge base directory does not exist: {self.directory_path}")
            return []

        all_documents = []
        logger.info(f"📁 Scanning knowledge base directory: {self.directory_path}")

        for root, dirs, files in os.walk(self.directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                ext = file.lower().split(".")[-1]
                
                try:
                    if ext == "json":
                        loader = JSONLoader(file_path)
                        docs = loader.load()
                        all_documents.extend(docs)
                        logger.debug(f"Loaded {len(docs)} document chunks from {file}")
                    
                    elif ext == "md":
                        loader = MarkdownLoader(file_path)
                        docs = loader.load()
                        all_documents.extend(docs)
                        logger.debug(f"Loaded {len(docs)} document chunks from {file}")
                    
                    elif ext == "pdf":
                        loader = PDFLoader(file_path)
                        docs = loader.load()
                        all_documents.extend(docs)
                        logger.debug(f"Loaded {len(docs)} document chunks from {file}")
                    
                    else:
                        # Skip other formats silently
                        continue
                        
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load file {file_path}: {e}")

        logger.success(f"🎉 Unified Loader: Successfully loaded {len(all_documents)} total raw document blocks.")
        return all_documents
