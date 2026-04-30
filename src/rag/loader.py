import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
from src.utils.logger import custom_logger as logger

class DocumentLoader:
    """
    Hospital Data Loader: Scans the data directory and loads PDFs/TXT files.
    """
    def __init__(self, data_path="data"):
        self.data_path = data_path

    def load_data(self):
        """Loads all supported files from the data directory."""
        logger.info(f"Loading documents from: {self.data_path}")
        
        # Check if directory exists
        if not os.path.exists(self.data_path):
            logger.error(f"Data directory not found: {self.data_path}")
            return []

        documents = []
        
        # Loading PDFs
        pdf_loader = DirectoryLoader(
            self.data_path, 
            glob="./*.pdf", 
            loader_cls=PyPDFLoader
        )
        
        # Loading Text/Markdown Files
        txt_loader = DirectoryLoader(
            self.data_path, 
            glob="./*.md", 
            loader_cls=TextLoader,
            loader_kwargs={'encoding': 'utf-8'}
        )

        try:
            documents.extend(pdf_loader.load())
            documents.extend(txt_loader.load())
            logger.info(f"Successfully loaded {len(documents)} pages/documents.")
            return documents
            
        except Exception as e:
            logger.error(f"Error while loading documents: {str(e)}")
            return []

if __name__ == "__main__":
    # Test Run
    loader = DocumentLoader()
    docs = loader.load_data()
    print(f"Total documents loaded: {len(docs)}")


        

        
        

