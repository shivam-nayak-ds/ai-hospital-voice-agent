"""
hospital_prompt.py
------------------
Centralised prompt templates for the RAG answer-generation layer.

All prompts are designed for voice-first delivery:
  - Short, spoken-paragraph style (no markdown, no bullet points)
  - Strict grounding in retrieved context (anti-hallucination)
  - Safe medical boundaries enforced explicitly
"""



# ─── RAG Answer Generation Prompt ────────────────────────────────────────────

RAG_SYSTEM_PROMPT = """\
You are Ananya, a warm and professional receptionist at Lifeline Multi-Speciality Hospital.
Your role is to answer callers' questions about hospital services, policies, departments, \
doctors, timings, and procedures — strictly based on the context provided below.

RULES (follow all of them without exception):
1. Answer ONLY from the provided context. If the answer is not in the context, say clearly:
   "I'm sorry, I don't have that information with me right now. You can call our front desk \
at extension 100 or visit us in person for more details."
2. Keep your response under 2 spoken sentences — callers are on the phone.
3. Use plain, friendly spoken language. No markdown, no bullet points, no asterisks.
4. NEVER provide medical diagnoses, treatment recommendations, or drug prescriptions.
5. NEVER invent facts, doctor names, room numbers, or prices not present in the context.
6. If the caller sounds distressed, gently suggest visiting our Emergency Department.
"""

RAG_USER_TEMPLATE = """\
--- Hospital Knowledge Base Context ---
{context}
--- End of Context ---

Caller Question: {question}

Spoken Answer (2 sentences max, plain text only):"""


def build_rag_prompt(context: str, question: str) -> str:
    """
    Builds the full RAG user message from retrieved context and the caller's question.

    Args:
        context:  Formatted string of retrieved document chunks.
        question: The caller's original query.

    Returns:
        Formatted prompt string ready for the LLM `user` role message.
    """
    return RAG_USER_TEMPLATE.format(context=context.strip(), question=question.strip())


# ─── Context Builder ──────────────────────────────────────────────────────────

def build_context_block(chunks: list, max_chunks: int = 3) -> str:
    """
    Formats a list of retrieved Document objects into a numbered context block
    with source citations.

    Args:
        chunks:     List of `Document` objects from HybridRetriever.
        max_chunks: Maximum number of chunks to include (top-N by rerank score).

    Returns:
        A multi-line string suitable for injection into RAG_USER_TEMPLATE.

    Example output:
        [1] (Source: FAQ.json | Category: billing)
        The consultation fee for Cardiology is Rs. 1,200.

        [2] (Source: hospital_policies/admission_policy.md | Category: policy)
        Patients must present a valid ID and insurance card at admission.
    """
    if not chunks:
        return "No relevant hospital information found."

    lines = []
    for i, doc in enumerate(chunks[:max_chunks], start=1):
        meta = doc.metadata or {}
        source = meta.get("source", "unknown")
        category = meta.get("category", "general")
        score = meta.get("rerank_score") or meta.get("score") or 0.0

        # Use short filename for readability
        source_short = source.split("/")[-1] if "/" in source else source
        header = f"[{i}] (Source: {source_short} | Category: {category} | Score: {score:.2f})"
        lines.append(header)
        lines.append(doc.page_content.strip())
        lines.append("")   # blank line between chunks

    return "\n".join(lines).strip()


# ─── Fallback Response Templates ──────────────────────────────────────────────

FALLBACK_NO_CONTEXT = (
    "I'm sorry, I couldn't find specific information about that in our knowledge base. "
    "Please call our front desk at extension 100 or visit the hospital reception for assistance."
)

FALLBACK_LOW_CONFIDENCE = (
    "I have some information on that, but I want to make sure it's accurate. "
    "Please confirm with our reception at extension 100 for the most up-to-date details."
)
