"""
Tool registry — sourced from cli_coding_agent/agent.py learning project.
Extended with _search_documents for RAG integration.
"""
import os
import json
import subprocess
import requests
from pathlib import Path
from typing import Callable, Dict


# ── Tool implementations ───────────────────────────────────────────────────────
def run_command(command: str) -> str:
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
        if result.returncode != 0:
            return f"Error (exit {result.returncode}): {error or output}"
        return output or "Command executed successfully with no output."
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"Error running command: {e}"


def write_file(args: str) -> str:
    try:
        data = json.loads(args)
        path, content = data["path"], data["content"]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File '{path}' written successfully ({len(content)} chars)."
    except json.JSONDecodeError:
        return "Error: input must be valid JSON with 'path' and 'content' keys."
    except Exception as e:
        return f"Error writing file: {e}"


def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def list_directory(path: str = ".") -> str:
    try:
        return "\n".join(os.listdir(path))
    except Exception as e:
        return f"Error listing directory: {e}"


def get_weather_report(location: str) -> str:
    try:
        url = f"https://wttr.in/{location.strip().lower()}?format=%C+%t+%m"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return f"Current weather in {location}: {resp.text.strip()}"
        return "Unable to fetch weather data at the moment."
    except Exception as e:
        return f"Error fetching weather: {e}"


def search_documents_placeholder(query: str) -> str:
    return "No documents have been uploaded yet. Please upload a PDF first."


# ── Registry ──────────────────────────────────────────────────────────────────
BASE_TOOL_REGISTRY: Dict[str, Callable] = {
    "_get_weather": get_weather_report,
    "_run_command": run_command,
    "_write_file": write_file,
    "_read_file": read_file,
    "_list_directory": list_directory,
    "_search_documents": search_documents_placeholder,
}

TOOL_DESCRIPTIONS = """
_get_weather(location: str)
  Input: plain string – city name.

_run_command(command: str)
  Input: shell command string. NOT for writing file content.

_write_file(json_string)
  Input: {"path": "...", "content": "..."}
  Creates or OVERWRITES a file. Use ONLY for brand-new files.

_read_file(path: str)
  Input: path to file.

_list_directory(path: str)
  Input: path to directory.

_search_documents(query: str)
  Input: plain string – what to search for.
  ALWAYS use this when the user asks about document content.
"""
