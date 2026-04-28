"""
ReAct Agent — production refactor of cli_coding_agent/agent.py.
Implements START → PLAN → TOOL → OBSERVE → OUTPUT loop as a reusable class.
"""
import json
import logging
from typing import Dict, Any, Callable, List, Optional

from openai import OpenAI
from app.config import get_settings
from app.agents.tools import BASE_TOOL_REGISTRY, TOOL_DESCRIPTIONS
from app.models.schemas import AgentStep

logger = logging.getLogger(__name__)
settings = get_settings()

SYSTEM_PROMPT_TEMPLATE = """You are DocuMind AI, an expert document intelligence assistant.
You solve user queries step by step using the START → PLAN → TOOL → OBSERVE → OUTPUT workflow.

CRITICAL RULES:
- Always respond with a single JSON object (never a list).
- Only one step per response. Wait for the next instruction.
- When asked about documents, ALWAYS use _search_documents first.
- ALL tool inputs that need JSON must be valid JSON strings.

Output JSON format:
{{
  "step": "START" | "PLAN" | "TOOL" | "OBSERVE" | "OUTPUT",
  "content": "string",
  "tool": "tool_name (only for TOOL step)",
  "input": "tool input (only for TOOL step)"
}}

Available tools:
{tool_descriptions}

{memory_context}
"""


class ReactAgent:
    """
    ReAct agent loop. Tools can be overridden at construction time,
    which allows injecting a RAG search tool bound to a specific Qdrant collection.
    """

    def __init__(self, tool_overrides: Optional[Dict[str, Callable]] = None):
        self.client = OpenAI(
            api_key=settings.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        self.tools = {**BASE_TOOL_REGISTRY}
        if tool_overrides:
            self.tools.update(tool_overrides)

    def run(
        self,
        user_query: str,
        memory_context: str = "",
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """Execute the ReAct loop. Returns answer + intermediate steps."""
        memory_block = (
            f"User Memory (personalise your response using this):\n{memory_context}"
            if memory_context
            else ""
        )
        system_content = SYSTEM_PROMPT_TEMPLATE.format(
            tool_descriptions=TOOL_DESCRIPTIONS,
            memory_context=memory_block,
        )

        messages: List[dict] = [{"role": "system", "content": system_content}]
        messages.append({"role": "user", "content": user_query})

        steps: List[dict] = []

        for iteration in range(max_iterations):
            try:
                response = self.client.chat.completions.parse(
                    model=settings.gemini_model_flash,
                    response_format=AgentStep,
                    messages=messages,
                )
                raw = response.choices[0].message.content
                parsed: AgentStep = response.choices[0].message.parsed
                messages.append({"role": "assistant", "content": raw})

                step = parsed.step
                step_data: dict = {"step": step, "content": parsed.content}
                logger.info("Agent [%s] iter=%d: %s", step, iteration + 1, str(parsed.content)[:80])

                if step in ("START", "PLAN", "OBSERVE"):
                    steps.append(step_data)
                    messages.append({"role": "user", "content": "Proceed."})

                elif step == "TOOL":
                    tool_name = parsed.tool or ""
                    tool_input = parsed.input or ""
                    step_data.update({"tool": tool_name, "input": tool_input})

                    if tool_name in self.tools:
                        tool_result = self.tools[tool_name](tool_input)
                    else:
                        tool_result = f"Error: tool '{tool_name}' not found."

                    step_data["result"] = tool_result[:600]
                    steps.append(step_data)

                    observe = json.dumps({
                        "step": "OBSERVE",
                        "tool": tool_name,
                        "input": tool_input,
                        "output": tool_result,
                    })
                    messages.append({"role": "user", "content": observe})

                elif step == "OUTPUT":
                    steps.append(step_data)
                    return {"answer": parsed.content, "steps": steps}

                else:
                    logger.warning("Unknown step '%s', stopping.", step)
                    break

            except Exception as e:
                logger.error("Agent error at iteration %d: %s", iteration + 1, e)
                return {"answer": f"I encountered an error: {e}", "steps": steps}

        return {
            "answer": "I reached the maximum reasoning steps without a final answer.",
            "steps": steps,
        }
