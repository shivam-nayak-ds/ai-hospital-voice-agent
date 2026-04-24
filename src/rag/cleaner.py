from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.utils.logger import custom_logger as logger

class TextCleaner:
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ".", " "],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        
    def clean(self, documents):
        """Cleans and splits documents into chunks for RAG."""
        logger.info(f"Cleaning {len(documents)} documents...")
        
        raw_texts = []
        for doc in documents:
            text = doc.page_content
            
            # 1. Newlines aur Tabs ko space mein badlo
            text = text.replace('\n', ' ').replace('\t', ' ')
            
            # 2. Faltu ke extra spaces hatao (e.g. "hello    world" -> "hello world")
            text = ' '.join(text.split())
            
            # 3. Strip trailing/leading spaces
            text = text.strip()
            
            if len(text) > 10: # Sirf kaam ka data rakho
                raw_texts.append(text)
        
        # Split into chunks
        chunks = self.splitter.create_documents(raw_texts)
        logger.info(f"Split into {len(chunks)} chunks.")
        return chunks

if __name__ == "__main__":
    # Test Run
    from langchain.schema import Document
    test_docs = [Document(page_content="City Care\nHospital\tSpecialists in\n\nHeart Care.")]
    cleaner = TextCleaner()
    res = cleaner.clean(test_docs)
    for c in res:
        print(f"Chunk: '{c.page_content}'")
