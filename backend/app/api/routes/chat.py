"""
Chat route — orchestrates Memory → ReAct Agent → LLM response.
POST /api/chat
"""
import logging
from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse, StepDetail
from app.agents.react_agent import ReactAgent
from app.services.memory_service import memory_service
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    1. Retrieve relevant user memories (mem0)
    2. Build a RAG search tool bound to the user's collection
    3. Run the ReAct agent loop
    4. Save the conversation turn to memory
    """
    try:
        # 1. Fetch memory context
        memory_ctx = memory_service.search(
            query=request.message,
            user_id=request.user_id,
        )

        # 2. Inject a RAG tool for the selected document collection
        search_tool = rag_service.make_search_tool(request.collection)
        agent = ReactAgent(model_id=request.model, tool_overrides={"_search_documents": search_tool})

        # 3. Run agent
        result = agent.run(
            user_query=request.message,
            memory_context=memory_ctx,
        )
        answer = result.get("answer", "")
        steps = [StepDetail(**s) for s in result.get("steps", [])]

        # 4. Save to memory (fire-and-forget; errors are non-fatal)
        memory_service.save(
            user_id=request.user_id,
            user_message=request.message,
            ai_response=answer,
        )

        return ChatResponse(
            message=answer,
            steps=steps,
            user_id=request.user_id,
            session_id=request.session_id,
        )

    except Exception as e:
        logger.error("Chat error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
