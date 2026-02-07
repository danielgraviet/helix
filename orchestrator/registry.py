import threading

import httpx

from models.skill import Skill, SkillStatus


class SkillRegistry:
    """In-memory registry that stores deployed skills and routes to them."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._lock = threading.Lock()

    def register(self, skill: Skill) -> None:
        """Add a skill to the registry."""
        with self._lock:
            self._skills[skill.name] = skill

    def lookup(self, name: str) -> Skill | None:
        """Find a skill by name. Returns None if not found."""
        with self._lock:
            return self._skills.get(name)

    def list_skills(self) -> list[dict]:
        """Return a summary of all registered skills (for Claude's tool context)."""
        with self._lock:
            return [
                {
                    "name": skill.name,
                    "description": skill.description,
                    "endpoint": skill.endpoint,
                    "status": skill.status.value,
                }
                for skill in self._skills.values()
            ]

    def remove(self, name: str) -> None:
        """Remove a skill from the registry."""
        with self._lock:
            self._skills.pop(name, None)

    def health_check(self) -> list[str]:
        """Ping /health on all registered skills. Prune dead ones. Return names of pruned skills."""
        with self._lock:
            snapshot = list(self._skills.items())
        pruned = []
        for name, skill in snapshot:
            if skill.status != SkillStatus.RUNNING:
                continue
            try:
                resp = httpx.get(f"http://localhost:{skill.port}/health", timeout=3)
                if resp.status_code != 200:
                    raise Exception("unhealthy")
            except Exception:
                skill.status = SkillStatus.STOPPED
                pruned.append(name)
        return pruned