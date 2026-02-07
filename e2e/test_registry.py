"""
Test the Skill Registry: register, lookup, list, health check, and pruning.
"""

import docker
import pytest

from models.skill import SkillSpec, SkillStatus
from orchestrator.registry import SkillRegistry
from skill_factory.factory import build_and_run, remove_skill


@pytest.fixture
def registry():
    return SkillRegistry()


@pytest.fixture
def live_skill():
    """Build a real skill container for integration tests."""
    spec = SkillSpec(
        name="test-greeter",
        description="Returns a greeting",
        execute_code='name = body.get("name", "world")\nreturn {"message": f"hello {name}"}',
        dependencies=[],
    )
    skill = build_and_run(spec)
    yield skill
    remove_skill(skill)


class TestRegistryUnit:
    """Unit tests — no Docker needed."""

    def test_register_and_lookup(self, registry, live_skill):
        registry.register(live_skill)
        found = registry.lookup("test-greeter")
        assert found is not None
        assert found.name == "test-greeter"

    def test_lookup_missing_returns_none(self, registry):
        assert registry.lookup("nonexistent") is None

    def test_list_skills(self, registry, live_skill):
        registry.register(live_skill)
        skills = registry.list_skills()
        assert len(skills) == 1
        assert skills[0]["name"] == "test-greeter"
        assert skills[0]["status"] == "running"

    def test_remove(self, registry, live_skill):
        registry.register(live_skill)
        registry.remove("test-greeter")
        assert registry.lookup("test-greeter") is None


class TestRegistryHealthCheck:
    """Integration tests — requires Docker."""

    def test_healthy_skill_stays_registered(self, registry, live_skill):
        """A running skill survives the health check."""
        registry.register(live_skill)
        pruned = registry.health_check()
        assert pruned == []
        assert registry.lookup("test-greeter").status == SkillStatus.RUNNING

    def test_dead_skill_gets_pruned(self, registry, live_skill):
        """After stopping a container, health check marks it as stopped."""
        registry.register(live_skill)

        # Kill the container behind the registry's back
        client = docker.from_env()
        container = client.containers.get(live_skill.container_id)
        container.stop(timeout=2)

        pruned = registry.health_check()
        assert "test-greeter" in pruned
        assert registry.lookup("test-greeter").status == SkillStatus.STOPPED
