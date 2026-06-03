from typing import List
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from src.utils.logger import custom_logger as logger
from src.rag.loaders.documents import Document

class MarkdownChunker:
    """
    Chunks Markdown documents structurally and semantically, enrich chunks with breadcrumbs and parent metadata.
    """
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 120):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 1. Setup Markdown Header Parser
        self.headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False  # Retain headers in text for dense representation context
        )

        # 2. Setup Semantic Recursive Splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )

    def chunk_document(self, doc: Document) -> List[Document]:
        """
        Splits a single Document into multiple structurally and semantically coherent chunk Documents.
        """
        if not doc.page_content.strip():
            return []

        # Step A: Parse structures by markdown headers
        try:
            header_splits = self.header_splitter.split_text(doc.page_content)
        except Exception as e:
            logger.error(f"Markdown header splitting failed for {doc.metadata.get('file_name', 'unknown')}: {e}")
            # Fallback to direct semantic splitting if header parsing fails
            header_splits = [Document(page_content=doc.page_content, metadata={})]

        chunks: List[Document] = []
        chunk_idx = 0

        # Step B: Segment structural splits semantically using Recursive Splitter
        for section in header_splits:
            section_text = section.page_content
            # Extracted headers metadata from Langchain split
            section_headers = section.metadata
            
            # Sub-split if section exceeds chunk size
            sub_splits = self.text_splitter.split_text(section_text)
            
            for sub_text in sub_splits:
                # Step C: Metadata Enrichment & Breadcrumbs context
                # Build breadcrumb context from H1 -> H4
                breadcrumb_parts = []
                last_header = None
                
                for header_key in ["Header 1", "Header 2", "Header 3", "Header 4"]:
                    header_val = section_headers.get(header_key)
                    if header_val:
                        breadcrumb_parts.append(str(header_val).strip())
                        last_header = str(header_val).strip()
                
                breadcrumb = " > ".join(breadcrumb_parts)
                
                # Prepend breadcrumbs to chunk text to enrich embedding context
                if breadcrumb:
                    enriched_content = f"Context: {breadcrumb}\n\nContent: {sub_text.strip()}"
                else:
                    enriched_content = sub_text.strip()

                # Merge parent metadata with chunk metadata
                chunk_metadata = doc.metadata.copy()
                chunk_metadata.update({
                    "breadcrumbs": breadcrumb,
                    "section": last_header or doc.metadata.get("category", "general"),
                    "chunk_idx": chunk_idx
                })
                
                # Generate unique chunk tracking ID in metadata
                file_stem = os.path.splitext(doc.metadata.get("file_name", "doc"))[0]
                chunk_metadata["chunk_id"] = f"{file_stem}:{chunk_idx}"

                chunk_doc = Document(page_content=enriched_content, metadata=chunk_metadata)
                chunks.append(chunk_doc)
                chunk_idx += 1

        return chunks

    def chunk_all(self, docs: List[Document]) -> List[Document]:
        """
        Chunks a list of documents and returns a consolidated list of chunks.
        """
        all_chunks = []
        for doc in docs:
            try:
                chunks = self.chunk_document(doc)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error(f"Failed to chunk document {doc.metadata.get('file_name', 'unknown')}: {e}")
                continue
        
        logger.info(f"Chunker: Created {len(all_chunks)} chunks from {len(docs)} source documents.")
        return all_chunks

import os
