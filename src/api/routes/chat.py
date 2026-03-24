"""Chat API endpoint for semantic search with LLM response generation."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from loguru import logger

from ...database import db
from ...embedder import Embedder, compose_text
from ...chat import ChatService
from ..schemas import ChatRequest, ChatResponse, ChatTechnology

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Chat endpoint: embed query, semantic search, generate LLM response.

    Falls back to text search if OpenAI is unavailable.
    Returns raw results if Claude is unavailable.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    query = request.query.strip()
    filters = request.filters
    history = [{"role": m.role, "content": m.content} for m in (request.history or [])]

    # Parse date filters
    from_date = None
    to_date = None
    if filters:
        if filters.from_date:
            try:
                from_date = datetime.fromisoformat(filters.from_date)
            except ValueError:
                pass
        if filters.to_date:
            try:
                to_date = datetime.fromisoformat(filters.to_date)
            except ValueError:
                pass

    fallback = False
    technologies = []
    similarity_scores = []

    # Step 1: Try semantic search
    try:
        embedder = Embedder()
        query_vector = embedder.embed_single(query)
        results = db.semantic_search(
            query_embedding=query_vector,
            university=filters.university if filters else None,
            top_field=filters.top_field if filters else None,
            subfield=filters.subfield if filters else None,
            patent_status=filters.patent_status if filters else None,
            from_date=from_date,
            to_date=to_date,
            limit=15,
        )
        technologies = [t for t, _ in results]
        similarity_scores = [s for _, s in results]
    except Exception as e:
        logger.warning(f"Semantic search failed, falling back to text search: {e}")
        fallback = True
        # Fall back to ILIKE text search
        try:
            text_results = db.text_search(
                query=query,
                university=filters.university if filters else None,
                top_field=filters.top_field if filters else None,
                subfield=filters.subfield if filters else None,
                patent_status=filters.patent_status if filters else None,
                from_date=from_date,
                to_date=to_date,
                limit=15,
            )
            technologies = text_results
            similarity_scores = [0.0] * len(text_results)
        except Exception as e2:
            logger.error(f"Text search also failed: {e2}")

    # Step 2: Try LLM response generation
    llm_available = True
    response_text = ""

    try:
        chat_service = ChatService()
        chat_response = chat_service.generate_response(
            query=query,
            technologies=technologies,
            similarity_scores=similarity_scores,
            history=history,
        )
        response_text = chat_response.text
        referenced = chat_response.referenced_technologies
    except Exception as e:
        logger.warning(f"Chat LLM failed: {e}")
        llm_available = False
        response_text = ""
        # Build referenced list from raw results
        referenced = []
        for tech, score in zip(technologies, similarity_scores):
            referenced.append({
                "uuid": str(tech.uuid),
                "title": tech.title,
                "university": tech.university,
                "similarity": round(score, 3),
                "description": (tech.description or "")[:200],
            })

    # Build response
    tech_list = [
        ChatTechnology(
            uuid=t["uuid"],
            title=t["title"],
            university=t["university"],
            similarity=t["similarity"],
            description=t["description"],
        )
        for t in referenced
    ]

    return ChatResponse(
        response=response_text,
        technologies=tech_list,
        fallback=fallback,
        llm_available=llm_available,
    )
