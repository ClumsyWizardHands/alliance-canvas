"""
Tools registry.

Loads the existing Open WebUI–shaped tool modules from ~/Desktop/workshop/tools/
via importlib, instantiates one `Tools()` per workspace with valves overridden
to match the workspace's folder_mounts, and exposes each tool's public methods
as OpenAI-style tool schemas for Ollama's native tool-calling.

Per-method docstrings drive the schema. We parse `:param NAME: DESCRIPTION`
blocks for parameter descriptions; the first non-`:param` paragraph becomes
the tool description.

Skills are NOT exposed here — Alliance Canvas's skills_runner is the
authoritative reader for the AgentSkills format. The legacy
`workshop/tools/skills.py` (flat-file globber) is loaded but its `list_skills` /
`load_skill` are shadowed by canvas-native equivalents.
"""

from __future__ import annotations

import importlib.util
import inspect
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .config import TOOLS_DIR


# Methods we actively shadow (the canvas backend provides these natively).
SHADOWED_METHODS = {
    ("skills", "list_skills"),
    ("skills", "load_skill"),
}


@dataclass
class ToolMethod:
    tool_id: str
    name: str
    description: str
    callable: Callable
    parameters_schema: dict[str, Any]


@dataclass
class LoadedTool:
    tool_id: str
    instance: Any
    methods: list[ToolMethod]
    error: str | None = None


def _load_module(tool_id: str, path: Path):
    spec = importlib.util.spec_from_file_location(f"workshop_tools_{tool_id}", path)
    if not spec or not spec.loader:
        raise ImportError(f"Could not create import spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _python_type_to_json_schema(annotation: Any) -> dict[str, Any]:
    """Best-effort mapping of Python type annotations to JSON Schema."""
    if annotation is inspect.Parameter.empty or annotation is None:
        return {"type": "string"}
    origin = getattr(annotation, "__origin__", None)
    args = getattr(annotation, "__args__", ())

    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is list or origin is list:
        item_schema = _python_type_to_json_schema(args[0]) if args else {"type": "string"}
        return {"type": "array", "items": item_schema}
    if annotation is dict or origin is dict:
        return {"type": "object"}
    # Optional[X] / X | None
    if origin is type(None):
        return {"type": "null"}
    if hasattr(annotation, "__class__") and "Union" in str(annotation.__class__):
        # Take the first non-None arg
        for a in args:
            if a is type(None):
                continue
            return _python_type_to_json_schema(a)
    # Fallback
    return {"type": "string"}


_PARAM_RE = re.compile(r":param\s+(\w+):\s*(.+?)(?=\n\s*:|\Z)", re.DOTALL)
_RETURN_RE = re.compile(r":return:\s*(.+?)(?=\n\s*:|\Z)", re.DOTALL)


def _parse_docstring(doc: str | None) -> tuple[str, dict[str, str]]:
    """Return (top-level description, {param_name: description})."""
    if not doc:
        return "", {}
    cleaned = inspect.cleandoc(doc)
    # Strip out :param: and :return: blocks for the description
    desc_part = _PARAM_RE.split(cleaned)[0]
    desc_part = _RETURN_RE.split(desc_part)[0]
    description = desc_part.strip()
    params: dict[str, str] = {}
    for m in _PARAM_RE.finditer(cleaned):
        params[m.group(1)] = re.sub(r"\s+", " ", m.group(2)).strip()
    return description, params


def _build_method_schema(name: str, fn: Callable) -> tuple[str, dict[str, Any]]:
    """Return (description, JSON Schema for parameters)."""
    sig = inspect.signature(fn)
    description, param_docs = _parse_docstring(fn.__doc__)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for pname, p in sig.parameters.items():
        if pname == "self":
            continue
        schema = _python_type_to_json_schema(p.annotation)
        if pname in param_docs:
            schema["description"] = param_docs[pname]
        properties[pname] = schema
        if p.default is inspect.Parameter.empty:
            required.append(pname)
    schema = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return description or fn.__name__, schema


def _apply_valves(instance: Any, overrides: dict[str, Any]) -> None:
    """Set valve fields on a Tools() instance from a flat dict."""
    valves = getattr(instance, "valves", None)
    if not valves:
        return
    for k, v in overrides.items():
        if hasattr(valves, k):
            setattr(valves, k, v)


def load_tools_for_workspace(valve_overrides: dict[str, dict[str, Any]]) -> dict[str, LoadedTool]:
    """
    Discover, import, and instantiate every Tools class in TOOLS_DIR.

    Returns {tool_id: LoadedTool}. Each LoadedTool carries a fresh instance
    with valves pre-applied for this workspace.
    """
    out: dict[str, LoadedTool] = {}
    if not TOOLS_DIR.exists():
        return out

    for py in sorted(TOOLS_DIR.glob("*.py")):
        if py.name.startswith("_"):
            continue
        tool_id = py.stem
        try:
            mod = _load_module(tool_id, py)
        except Exception as e:
            out[tool_id] = LoadedTool(tool_id=tool_id, instance=None, methods=[], error=f"import failed: {e}")
            continue

        Tools = getattr(mod, "Tools", None)
        if Tools is None:
            out[tool_id] = LoadedTool(tool_id=tool_id, instance=None, methods=[], error="no Tools class")
            continue

        try:
            instance = Tools()
        except Exception as e:
            out[tool_id] = LoadedTool(tool_id=tool_id, instance=None, methods=[], error=f"instantiation failed: {e}")
            continue

        _apply_valves(instance, valve_overrides.get(tool_id, {}))

        methods: list[ToolMethod] = []
        for mname, mfn in inspect.getmembers(instance, predicate=inspect.ismethod):
            if mname.startswith("_"):
                continue
            if (tool_id, mname) in SHADOWED_METHODS:
                continue
            description, params_schema = _build_method_schema(mname, mfn)
            methods.append(
                ToolMethod(
                    tool_id=tool_id,
                    name=mname,
                    description=description,
                    callable=mfn,
                    parameters_schema=params_schema,
                )
            )
        out[tool_id] = LoadedTool(tool_id=tool_id, instance=instance, methods=methods)

    return out


def to_ollama_tool_schemas(loaded: dict[str, LoadedTool], allowlist: set[str] | None = None) -> list[dict]:
    """
    Flatten every method into the Ollama/OpenAI tool schema list.

    If `allowlist` is provided, only methods whose tool_id is in the allowlist
    are exposed. (Workspace `active_tools` controls this.)
    """
    schemas: list[dict] = []
    for tool_id, lt in loaded.items():
        if lt.error:
            continue
        if allowlist is not None and tool_id not in allowlist:
            continue
        for m in lt.methods:
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": m.name,
                        "description": m.description,
                        "parameters": m.parameters_schema,
                    },
                }
            )
    return schemas


def find_method(loaded: dict[str, LoadedTool], method_name: str) -> ToolMethod | None:
    """Look up a method by its (globally unique) name across all loaded tools."""
    for lt in loaded.values():
        for m in lt.methods:
            if m.name == method_name:
                return m
    return None


def call_method(method: ToolMethod, args: dict[str, Any]) -> str:
    """Invoke a tool method with kwargs, return its (always-string) result."""
    try:
        result = method.callable(**(args or {}))
        if not isinstance(result, str):
            return str(result)
        return result
    except TypeError as e:
        return (
            f"Tool {method.tool_id}.{method.name} called with bad arguments: {e}\n"
            f"Re-read the tool's parameter list and retry. CEP-13 applies — "
            f"check the tool's actual signature before declaring it broken."
        )
    except Exception as e:
        return (
            f"Tool {method.tool_id}.{method.name} failed: {type(e).__name__}: {e}\n"
            f"Surface to Alex if this recurs. CEP-13 applies."
        )


def loaded_to_dict(lt: LoadedTool) -> dict[str, Any]:
    return {
        "tool_id": lt.tool_id,
        "error": lt.error,
        "methods": [
            {
                "name": m.name,
                "description": m.description,
                "parameters": m.parameters_schema,
            }
            for m in lt.methods
        ],
    }
