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
- Always respond with a single JSON object (never a list, never plain text).
- Only one step per response. Wait for the next instruction.
- When asked about documents, ALWAYS use _search_documents first.
- ALL tool inputs that need JSON must be valid JSON strings.

Output JSON format:
{{
  "step": "START" | "PLAN" | "TOOL" | "OBSERVE" | "OUTPUT",
  "content": "string",
  "tool": "tool_name (only for TOOL step, otherwise omit)",
  "input": "tool input (only for TOOL step, otherwise omit)"
}}

Available tools:
{tool_descriptions}

{memory_context}
"""


class ReactAgent:
    """
    ReAct agent loop. Supports multiple LLMs (Gemini, OpenAI, DeepSeek).
    Tools can be overridden at construction time.
    Uses json_object mode + manual parsing for universal compatibility.
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
        else:  # Default: Gemini via OpenAI-compatible endpoint
            self.client = OpenAI(
                api_key=settings.gemini_api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
            self.model_name = settings.gemini_model_flash

    def _call_llm(self, messages: List[dict]) -> AgentStep:
        """
        Call the LLM with json_object response format and parse the result.
        This approach works with Gemini, OpenAI, and DeepSeek uniformly.
        """
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            response_format={"type": "json_object"},
            max_tokens=1024,
            temperature=0.2,
        )
        raw = response.choices[0].message.content
        if not raw:
            raise ValueError("LLM returned empty response.")
        try:
            parsed_dict = json.loads(raw)
        except json.JSONDecodeError as e:
            # Attempt to extract JSON from markdown code block
            import re
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if match:
                parsed_dict = json.loads(match.group(1))
            else:
                raise ValueError(f"LLM returned invalid JSON: {e}\nRaw: {raw[:200]}")
        return raw, AgentStep(**parsed_dict)

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
                raw, parsed = self._call_llm(messages)
                messages.append({"role": "assistant", "content": raw})

                step = parsed.step
                step_data: dict = {"step": step, "content": parsed.content}
                logger.info(
                    "Agent [%s] (%s) iter=%d: %s",
                    step, self.model_id, iteration + 1, str(parsed.content)[:80],
                )

                if step in ("START", "PLAN", "OBSERVE"):
                    steps.append(step_data)
                    messages.append({"role": "user", "content": "Proceed to the next step."})

                elif step == "TOOL":
                    tool_name = parsed.tool or ""
                    tool_input = parsed.input or ""
                    step_data.update({"tool": tool_name, "input": tool_input})

                    if tool_name in self.tools:
                        try:
                            tool_result = self.tools[tool_name](tool_input)
                        except Exception as te:
                            tool_result = f"Tool '{tool_name}' raised an error: {te}"
                    else:
                        tool_result = f"Error: tool '{tool_name}' not found. Available: {list(self.tools.keys())}"

                    step_data["result"] = str(tool_result)[:600]
                    steps.append(step_data)

                    observe_msg = json.dumps({
                        "step": "OBSERVE",
                        "tool": tool_name,
                        "input": tool_input,
                        "output": str(tool_result)[:1000],
                    })
                    messages.append({"role": "user", "content": observe_msg})

                elif step == "OUTPUT":
                    steps.append(step_data)
                    return {"answer": parsed.content or "No answer generated.", "steps": steps}

                else:
                    logger.warning("Unknown step '%s', stopping.", step)
                    break

            except Exception as e:
                logger.error("Agent error at iteration %d: %s", iteration + 1, e, exc_info=True)
                return {
                    "answer": f"I encountered an error while reasoning: {e}",
                    "steps": steps,
                }

        return {
            "answer": "I reached the maximum reasoning steps. Please try a simpler query.",
            "steps": steps,
        }
