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
    ReAct agent loop. Supports multiple LLMs (Gemini, OpenAI, DeepSeek).
    Tools can be overridden at construction time.
    """

    def __init__(self, model_id: str = "gemini", tool_overrides: Optional[Dict[str, Callable]] = None):
        self.model_id = model_id.lower()
        self.tools = {**BASE_TOOL_REGISTRY}
        if tool_overrides:
            self.tools.update(tool_overrides)
        
        self._setup_client()

    def _setup_client(self):
        """Configure the OpenAI client based on the selected model_id."""
        if self.model_id == "openai":
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.model_name = "gpt-4o"
        elif self.model_id == "deepseek":
            self.client = OpenAI(
                api_key=settings.deepseek_api_key,
                base_url="https://api.deepseek.com",
            )
            self.model_name = "deepseek-chat"
        else:  # Default: Gemini
            self.client = OpenAI(
                api_key=settings.gemini_api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
            self.model_name = settings.gemini_model_flash

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
                # DeepSeek and older models might not support .parse() with Pydantic schemas yet
                # For compatibility, we'll use a standard chat completion and parse JSON manually if needed
                # However, Gemini/OpenAI support .parse(). DeepSeek doesn't support structured output via SDK yet.
                
                if self.model_id == "deepseek":
                    response = self.client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        response_format={"type": "json_object"},
                    )
                    raw = response.choices[0].message.content
                    parsed_dict = json.loads(raw)
                    parsed = AgentStep(**parsed_dict)
                else:
                    response = self.client.chat.completions.parse(
                        model=self.model_name,
                        response_format=AgentStep,
                        messages=messages,
                    )
                    raw = response.choices[0].message.content
                    parsed = response.choices[0].message.parsed

                messages.append({"role": "assistant", "content": raw})

                step = parsed.step
                step_data: dict = {"step": step, "content": parsed.content}
                logger.info("Agent [%s] (%s) iter=%d: %s", step, self.model_id, iteration + 1, str(parsed.content)[:80])

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
                return {"answer": f"I encountered an error while reasoning: {e}", "steps": steps}

        return {
            "answer": "I reached the maximum reasoning steps without a final answer.",
            "steps": steps,
        }
