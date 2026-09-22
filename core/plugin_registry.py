"""Self-describing local skill registry for JARVIS."""
from __future__ import annotations
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Callable, Any

@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    handler: Callable[..., Any]
    source: str

class SkillRegistry:
    def __init__(self, package: str="actions"):
        self.package=package
        self.skills: dict[str,Skill]={}

    def discover(self) -> list[Skill]:
        self.skills.clear()
        try:
            pkg=import_module(self.package)
            root=Path(pkg.__file__).parent
        except Exception:
            return []
        for path in root.glob("*.py"):
            if path.name.startswith("_") or path.stem=="__init__":
                continue
            try:
                mod=import_module(f"{self.package}.{path.stem}")
            except Exception:
                continue
            meta=getattr(mod,"TOOL",None) or getattr(mod,"PLUGIN",None)
            handler=getattr(mod,"run",None) or getattr(mod,"execute",None)
            if isinstance(meta,dict) and callable(handler):
                name=str(meta.get("name",path.stem))
                desc=str(meta.get("description",""))
                self.skills[name]=Skill(name,desc,handler,f"{self.package}.{path.stem}")
        return list(self.skills.values())

    def describe(self) -> str:
        skills=list(self.skills.values()) or self.discover()
        if not skills:
            return "No self-describing skills were discovered."
        return "\n".join(f"- {s.name}: {s.description}" for s in skills)
