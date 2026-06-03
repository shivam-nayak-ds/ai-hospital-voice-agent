import sys
import uuid
import hashlib
import pickle
import time
from pathlib import Path
from typing import List

# Ensure project root is in PYTHONPATH
sys.path.append(str(Path(__file__).resolve().parents[2]))

from qdrant_client import QdrantClient
from qdrant_client.http import models

from src.rag.faq.pipeline import FAQPipeline
from src.rag.loaders.knowledge_base_loader import KnowledgeBaseLoader
from src.rag.processing.validator import DocumentValidator
from src.rag.processing.metadata_handler import MetadataExtractor
from src.rag.processing.chunker import MarkdownChunker

from src.rag.embeddings.embedding_model import EmbeddingModel
from src.rag.vectordb.qdrant_client import get_qdrant_client
from src.rag.vectordb.collections import recreate_collection, create_collection
from src.rag.config.settings import rag_settings
from src.utils.logger import custom_logger as logger

def ingest_faqs(batch_size: int = 32) -> List[models.PointStruct]:
    """
    Orchestrates structured FAQ Ingestion Pipeline.
    Returns list of processed Qdrant PointStruct items.
    """
    logger.info("STARTING FAQ INGESTION RUNNER")
    try:
        pipeline = FAQPipeline()
        documents = pipeline.run()
        if not documents:
            logger.error("No documents compiled by FAQ pipeline.")
            return []
        logger.info(f"Loaded {len(documents)} FAQ documents for ingestion.")
    except Exception as e:
        logger.critical(f"Failed to execute FAQ pipeline: {e}")
        return []

    try:
        client = get_qdrant_client()
        recreate_collection(
            client=client, 
            collection_name=rag_settings.FAQ_COLLECTION, 
            vector_size=rag_settings.EMBEDDING_DIMENSION
        )
    except Exception as e:
        logger.critical(f"Failed to connect or configure Qdrant: {e}")
        return []

    try:
        embedder = EmbeddingModel()
    except Exception as e:
        logger.critical(f"Failed to initialize embedding model: {e}")
        return []

    points = []
    total_docs = len(documents)
    logger.info(f"Generating dense embeddings for FAQs in batches of {batch_size}...")

    for i in range(0, total_docs, batch_size):
        batch = documents[i : i + batch_size]
        batch_texts = [doc.page_content for doc in batch]

        try:
            vectors = embedder.embed_documents(batch_texts)
            for doc, vector in zip(batch, vectors):
                faq_id = doc.metadata.get("id", str(uuid.uuid4()))
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, faq_id))
                payload = {
                    "page_content": doc.page_content,
                    **doc.metadata
                }
                points.append(models.PointStruct(id=point_id, vector=vector, payload=payload))
        except Exception as e:
            logger.error(f"Failed to generate FAQ embeddings for batch {i}-{i+len(batch)}: {e}")
            continue

    if points:
        try:
            upsert_batch_size = 100
            for start_idx in range(0, len(points), upsert_batch_size):
                batch_points = points[start_idx : start_idx + upsert_batch_size]
                client.upsert(
                    collection_name=rag_settings.FAQ_COLLECTION,
                    points=batch_points,
                    wait=True
                )
            logger.success(f"Successfully ingested {len(points)} FAQ points into Qdrant collection '{rag_settings.FAQ_COLLECTION}' in batches.")
        except Exception as e:
            logger.error(f"Failed to upload FAQ points to Qdrant: {e}")
    
    return points

def ingest_markdown(batch_size: int = 32, force_reload: bool = False) -> List[models.PointStruct]:
    """
    Orchestrates Markdown Ingestion Pipeline:
    1. Scan raw markdown files recursively.
    2. Validate and enrich metadata fields.
    3. Structural & Semantic chunking (800 size, 120 overlap).
    4. Content hashing and duplicate detection using Qdrant point retrieval.
    5. Local embedding generation and bulk upsert.
    """
    logger.info("STARTING MARKDOWN INGESTION RUNNER")
    start_time = time.time()

    # 1. Recursive file discovery & load
    try:
        kb_loader = KnowledgeBaseLoader("data/raw/internal")
        all_raw_docs = kb_loader.load_all()
        # Keep only markdown files
        markdown_docs = [doc for doc in all_raw_docs if doc.metadata.get("source", "").endswith(".md")]
        logger.info(f"Discovered {len(markdown_docs)} markdown files in internal folder.")
    except Exception as e:
        logger.critical(f"Failed to load raw markdown files: {e}")
        return []

    # 2. Validation & Cleaning
    validator = DocumentValidator()
    validated_docs = validator.validate_all(markdown_docs)

    # 3. Metadata Extraction & Standardizing
    metadata_extractor = MetadataExtractor()
    enriched_docs = metadata_extractor.process_all(validated_docs)

    # 4. Structural & Semantic Chunking
    chunker = MarkdownChunker(chunk_size=800, chunk_overlap=120)
    chunks = chunker.chunk_all(enriched_docs)
    if not chunks:
        logger.warning("No markdown chunks generated. Aborting markdown ingestion.")
        return []

    # 5. Qdrant Setup
    try:
        client = get_qdrant_client()
        # Ensure collection exists, recreate only if force_reload is true
        if force_reload:
            recreate_collection(
                client=client, 
                collection_name=rag_settings.MARKDOWN_COLLECTION, 
                vector_size=rag_settings.EMBEDDING_DIMENSION
            )
        else:
            create_collection(
                client=client, 
                collection_name=rag_settings.MARKDOWN_COLLECTION, 
                vector_size=rag_settings.EMBEDDING_DIMENSION
            )
    except Exception as e:
        logger.critical(f"Failed to connect or configure Qdrant for markdown: {e}")
        return []

    # 6. Content Hashing & Duplicate Cache Checking
    logger.info("Performing content hash and duplicate cache checks...")
    final_points = []
    chunks_to_embed = []
    chunks_to_embed_indices = []

    # Generate hashes and deterministic IDs
    for idx, chunk in enumerate(chunks):
        content_bytes = chunk.page_content.encode("utf-8")
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        
        # Inject content hash in metadata
        chunk.metadata["content_hash"] = content_hash
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, content_hash))
        
        chunks_to_embed.append(chunk)
        chunks_to_embed_indices.append((point_id, chunk))

    # Retrieve existing IDs from Qdrant to skip embedding unchanged texts
    existing_ids = set()
    # Bypass retrieve cache check on Qdrant Cloud to prevent socket pooling hangs on Windows.
    # Since Point IDs are deterministic UUIDs of content hashes, upserts are completely idempotent.
    logger.info("Bypassing duplicate check for stability. Proceeding with full idempotent upsert.")

    # 7. Embedding Generation for new chunks
    try:
        embedder = EmbeddingModel()
    except Exception as e:
        logger.critical(f"Failed to initialize embedding model: {e}")
        return []

    points_to_upsert = []
    skipped_count = 0
    
    # Process only non-existing chunks
    filtered_indices = [item for item in chunks_to_embed_indices if item[0] not in existing_ids]
    logger.info(f"Ingestion Queue: {len(filtered_indices)} chunks to embed (Skipped: {len(existing_ids)}).")

    for i in range(0, len(filtered_indices), batch_size):
        batch = filtered_indices[i : i + batch_size]
        batch_texts = [item[1].page_content for item in batch]
        
        try:
            vectors = embedder.embed_documents(batch_texts)
            for (point_id, chunk), vector in zip(batch, vectors):
                payload = {
                    "page_content": chunk.page_content,
                    **chunk.metadata
                }
                points_to_upsert.append(
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                )
        except Exception as e:
            logger.error(f"Failed to generate embeddings for batch {i}-{i+len(batch)}: {e}")
            continue

    # 8. Bulk Upsert in batches of 100 to prevent request timeouts on cloud endpoints
    if points_to_upsert:
        try:
            upsert_batch_size = 100
            logger.info(f"Upserting {len(points_to_upsert)} chunks to Qdrant collection '{rag_settings.MARKDOWN_COLLECTION}' in batches of {upsert_batch_size}...")
            for start_idx in range(0, len(points_to_upsert), upsert_batch_size):
                batch_points = points_to_upsert[start_idx : start_idx + upsert_batch_size]
                client.upsert(
                    collection_name=rag_settings.MARKDOWN_COLLECTION,
                    points=batch_points,
                    wait=True
                )
            logger.success(f"Successfully upserted {len(points_to_upsert)} new markdown chunks.")
        except Exception as e:
            logger.error(f"Failed to upsert markdown points to Qdrant: {e}")
    else:
        logger.info("No new markdown chunks to upsert.")

    duration = time.time() - start_time
    logger.info(f"MARKDOWN INGESTION RUN COMPLETED (Time: {duration:.2f}s, Chunks Created: {len(chunks)}, Duplicates Skipped: {len(existing_ids)})")
    return points_to_upsert

def compile_bm25_corpus() -> None:
    """
    Compiles a unified BM25 local search index by loading and processing
    all FAQ documents and Markdown chunks, saving the result to a pickle file.
    """
    logger.info("STARTING UNIFIED BM25 CORPUS COMPILATION")
    
    # 1. Load and process FAQs
    faq_docs = []
    try:
        faq_pipeline = FAQPipeline()
        faq_docs = faq_pipeline.run()
        logger.info(f"BM25: Compiled {len(faq_docs)} FAQ documents.")
    except Exception as e:
        logger.error(f"Failed to run FAQ pipeline for BM25: {e}")

    # 2. Load and process Markdown
    md_chunks = []
    try:
        kb_loader = KnowledgeBaseLoader("data/raw/internal")
        all_raw_docs = kb_loader.load_all()
        markdown_docs = [doc for doc in all_raw_docs if doc.metadata.get("source", "").endswith(".md")]
        
        validator = DocumentValidator()
        validated_docs = validator.validate_all(markdown_docs)
        
        metadata_extractor = MetadataExtractor()
        enriched_docs = metadata_extractor.process_all(validated_docs)
        
        chunker = MarkdownChunker(chunk_size=800, chunk_overlap=120)
        md_chunks = chunker.chunk_all(enriched_docs)
        logger.info(f"BM25: Compiled {len(md_chunks)} Markdown chunk documents.")
    except Exception as e:
        logger.error(f"Failed to parse Markdown files for BM25: {e}")

    # 3. Combine and Serialize
    unified_corpus = faq_docs + md_chunks
    if not unified_corpus:
        logger.warning("No corpus documents compiled for BM25. Aborting serialization.")
        return

    try:
        processed_dir = Path("data/processed")
        processed_dir.mkdir(parents=True, exist_ok=True)
        corpus_path = processed_dir / "bm25_corpus.pkl"
        
        with open(corpus_path, "wb") as f:
            pickle.dump(unified_corpus, f)
            
        logger.success(f"Successfully compiled and serialized {len(unified_corpus)} documents to {corpus_path}")
    except Exception as e:
        logger.error(f"Failed to write BM25 corpus to pickle file: {e}")

def run_full_ingestion():
    """
    Runner to execute both ingestion pipelines and compile the unified BM25 index.
    """
    logger.info("RUNNING FULL SYSTEM INGESTION PROCESS")
    
    # Run FAQs ingestion
    ingest_faqs()
    
    # Run Markdown ingestion
    ingest_markdown(force_reload=False)
    
    # Compile BM25 index
    compile_bm25_corpus()
    
    logger.info("FULL SYSTEM INGESTION PROCESS COMPLETED")

if __name__ == "__main__":
    run_full_ingestion()
