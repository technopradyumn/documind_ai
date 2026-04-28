"""
LangGraph workflow — sourced from langGraph/chat_checkpoint.py
& langGraph/conditional_chat.py learning modules.

Adds conditional routing (fast vs detailed model) with MongoDB
checkpointing for persistent conversation history per user session.
"""
import logging
from typing import Annotated, Literal, Optional

from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.mongodb import MongoDBSaver

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ── State ─────────────────────────────────────────────────────────────────────
class ConversationState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str
    complexity: Optional[str]


# ── LLM clients ───────────────────────────────────────────────────────────────
_llm_flash = ChatGoogleGenerativeAI(
    model=settings.gemini_model_flash,
    google_api_key=settings.gemini_api_key,
    temperature=0.1,
)
_llm_pro = ChatGoogleGenerativeAI(
    model=settings.gemini_model_pro,
    google_api_key=settings.gemini_api_key,
    temperature=0.3,
)


# ── Nodes ─────────────────────────────────────────────────────────────────────
def _route_by_complexity(state: ConversationState) -> Literal["fast_chat", "detailed_chat"]:
    """Conditional edge — route simple queries to flash, complex to pro."""
    last = state["messages"][-1].content if state["messages"] else ""
    complex_keywords = ["analyze", "compare", "summarize", "explain", "write", "create", "code", "review"]
    if any(kw in last.lower() for kw in complex_keywords) or len(last) > 300:
        return "detailed_chat"
    return "fast_chat"


def fast_chat_node(state: ConversationState) -> dict:
    response = _llm_flash.invoke(state["messages"])
    return {"messages": [response], "complexity": "simple"}


def detailed_chat_node(state: ConversationState) -> dict:
    response = _llm_pro.invoke(state["messages"])
    return {"messages": [response], "complexity": "complex"}


# ── Graph factory ─────────────────────────────────────────────────────────────
def _build_graph(checkpointer=None) -> StateGraph:
    builder = StateGraph(ConversationState)
    builder.add_node("fast_chat", fast_chat_node)
    builder.add_node("detailed_chat", detailed_chat_node)
    builder.add_conditional_edges(START, _route_by_complexity)
    builder.add_edge("fast_chat", END)
    builder.add_edge("detailed_chat", END)
    return builder.compile(checkpointer=checkpointer)


# ── Public class ──────────────────────────────────────────────────────────────
class LangGraphAgent:
    """Stateful chat agent with MongoDB-persisted conversation threads."""

    def __init__(self):
        # Fallback stateless graph (no checkpointer)
        self._stateless = _build_graph()

    def chat(self, message: str, user_id: str, session_id: str) -> str:
        thread_id = f"{user_id}:{session_id}"
        config = {"configurable": {"thread_id": thread_id}}
        input_state = {
            "messages": [message],
            "user_id": user_id,
            "complexity": None,
        }
        try:
            with MongoDBSaver.from_conn_string(settings.mongodb_uri) as checkpointer:
                graph = _build_graph(checkpointer=checkpointer)
                result = graph.invoke(input_state, config=config)
                return result["messages"][-1].content
        except Exception as e:
            logger.warning("MongoDB checkpointer unavailable (%s). Falling back to stateless.", e)
            result = self._stateless.invoke(input_state)
            return result["messages"][-1].content
