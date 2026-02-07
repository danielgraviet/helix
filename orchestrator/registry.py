import httpx

from models.skill import Skill, SkillStatus


class SkillRegistry:
    """In-memory registry that stores deployed skills and routes to them."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """Add a skill to the registry."""
        self._skills[skill.name] = skill

    def lookup(self, name: str) -> Skill | None:
        """Find a skill by name. Returns None if not found."""
        return self._skills.get(name)

    def list_skills(self) -> list[dict]:
        """Return a summary of all registered skills (for Claude's tool context)."""
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
        self._skills.pop(name, None)

    def health_check(self) -> list[str]:
        """Ping /health on all registered skills. Prune dead ones. Return names of pruned skills."""
        pruned = []
        for name, skill in list(self._skills.items()):
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