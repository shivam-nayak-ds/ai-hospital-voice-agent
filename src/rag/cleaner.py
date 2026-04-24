import re
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.utils.logger import custom_logger as logger

class TextCleaner:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ".", " ", ""],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        
    def clean(self, documents: List[Document]) -> List[Document]:
        """
        Cleans documents by removing noise but preserving structure for splitting.
        """
        logger.info(f"Cleaning {len(documents)} documents for RAG...")
        
        cleaned_docs = []
        for doc in documents:
            text = doc.page_content
            
            # Remove only excessive horizontal whitespace, keep vertical for splitter
            text = re.sub(r' +', ' ', text)  # Multi-space to single
            text = text.replace('\t', ' ')   # Tabs to space
            
            doc.page_content = text.strip()
            if len(doc.page_content) > 10:
                cleaned_docs.append(doc)
        
        # Split documents (preserving metadata)
        chunks = self.splitter.split_documents(cleaned_docs)
        logger.success(f"Transformation complete. Generated {len(chunks)} smart chunks.")
        return chunks

if __name__ == "__main__":
    # Test Run
    from langchain.schema import Document
    test_docs = [Document(page_content="City Care\nHospital\tSpecialists in\n\nHeart Care.")]
    cleaner = TextCleaner()
    res = cleaner.clean(test_docs)
    for c in res:
        print(f"Chunk: '{c.page_content}'")
