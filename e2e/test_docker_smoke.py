"""
Smoke test: verify docker-py can build an image, run a container on agent-net,
and hit an HTTP endpoint.
"""

import tempfile
import time
from pathlib import Path

import docker
import httpx
import pytest

import config

_SMOKE_TEST_PORT = 9999


@pytest.fixture
def docker_client():
    client = docker.from_env() # what does from env mean? I do not have any .env files.
    yield client
    client.close()


@pytest.fixture
def smoke_container(docker_client):
    """Build and run a minimal FastAPI container, then clean up after the test."""
    container = None
    image_tag = "seaf-smoke-test:latest"

    with tempfile.TemporaryDirectory() as build_dir:
        # Write a minimal FastAPI app
        app_code = Path(build_dir) / "main.py"
        
        # writes file to local machine.
        app_code.write_text(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            "\n"
            "@app.get('/health')\n"
            "def health():\n"
            "    return {'status': 'ok'}\n"
            "\n"
            "@app.post('/execute')\n"
            "def execute():\n"
            "    return {'result': 'smoke test passed'}\n"
        )

        # Write a minimal Dockerfile
        dockerfile = Path(build_dir) / "Dockerfile"
        
        # takes main.py which is a file from local machine and writes it to docker.
        dockerfile.write_text(
            f"FROM {config.SKILL_BASE_IMAGE}\n"
            "RUN pip install --no-cache-dir fastapi uvicorn\n"
            "WORKDIR /app\n"
            "COPY main.py .\n"
            'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]\n'
        )

        # Build image
        docker_client.images.build(path=build_dir, tag=image_tag, rm=True)

        # Run container
        container = docker_client.containers.run(
            image_tag,
            detach=True,
            ports={"8000/tcp": _SMOKE_TEST_PORT}, # how does this port come into play? is it localhost:8000/tcp?
            network=config.DOCKER_NETWORK,
            name="seaf-smoke-test",
        )

    yield container

    # Cleanup
    container.stop(timeout=5)
    container.remove()
    docker_client.images.remove(image_tag, force=True)


def wait_for_healthy(port: int, timeout: int = config.SKILL_STARTUP_TIMEOUT):
    """Poll /health until the container is ready."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = httpx.get(f"http://localhost:{port}/health", timeout=2)
            if resp.status_code == 200:
                return True
        except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError):
            time.sleep(0.5)
    return False


class TestDockerSmoke:
    def test_container_starts_and_is_healthy(self, smoke_container):
        """Container comes up and /health returns 200."""
        assert smoke_container.status in ("created", "running")
        healthy = wait_for_healthy(_SMOKE_TEST_PORT)
        assert healthy, f"Container failed to become healthy within {config.SKILL_STARTUP_TIMEOUT}s"

    def test_execute_endpoint(self, smoke_container):
        """/execute returns expected response."""
        wait_for_healthy(_SMOKE_TEST_PORT)
        resp = httpx.post(f"http://localhost:{_SMOKE_TEST_PORT}/execute")
        assert resp.status_code == 200
        assert resp.json() == {"result": "smoke test passed"}

    def test_container_on_agent_network(self, docker_client, smoke_container):
        """Container is attached to the agent-net bridge network."""
        network = docker_client.networks.get(config.DOCKER_NETWORK)
        container_ids = [c.id for c in network.containers]
        assert smoke_container.id in container_ids
