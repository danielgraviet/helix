import shutil
import textwrap
import time
from pathlib import Path

import docker
import httpx
from jinja2 import Environment, FileSystemLoader

import config
from models.skill import Skill, SkillSpec, SkillStatus
from skill_factory.port_manager import allocate_port

# Jinja2 setup — load templates from the templates directory
TEMPLATE_DIR = Path(__file__).parent / "templates" / "fastapi_skill"
BUILDS_DIR = Path(__file__).parent / "builds"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))


def render_skill(spec: SkillSpec) -> dict[str, str]:
    """Render the Jinja2 templates into source files using a SkillSpec."""
    # Indent code blocks to sit inside their try blocks (8 spaces)
    indented_code = textwrap.indent(spec.execute_code, "        ")
    indented_view_post = textwrap.indent(spec.view_post_code, "        ")

    main_py = jinja_env.get_template("main.py.j2").render(
        skill_name=spec.name,
        execute_code=indented_code,
        view_post_code=indented_view_post,
    )

    dockerfile = jinja_env.get_template("Dockerfile.j2").render(
        base_image=config.SKILL_BASE_IMAGE,
        dependencies=spec.dependencies,
    )

    return {"main.py": main_py, "Dockerfile": dockerfile}


def build_and_run(spec: SkillSpec) -> Skill:
    """Take a SkillSpec, build a Docker image, run the container, return a Skill."""
    client = docker.from_env()
    port = allocate_port()
    image_tag = f"seaf-skill-{spec.name}:latest"

    # Render templates to source files
    files = render_skill(spec)

    # Write source files to persistent builds directory
    build_dir = BUILDS_DIR / spec.name
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    for filename, content in files.items():
        (build_dir / filename).write_text(content)

    # Build image
    try:
        client.images.build(
            path=str(build_dir),
            tag=image_tag,
            rm=True,
            timeout=config.CONTAINER_TIMEOUT,
        )
    except docker.errors.BuildError as e:
        build_log = "\n".join(line.get("stream", "") for line in e.build_log if "stream" in line)
        raise RuntimeError(f"Docker build failed:\n{build_log}") from e

    # Run container
    container = client.containers.run(
        image_tag,
        detach=True,
        ports={"8000/tcp": port},
        network=config.DOCKER_NETWORK,
        name=f"seaf-{spec.name}",
    )

    # Build the Skill object
    skill = Skill(
        name=spec.name,
        description=spec.description,
        endpoint=f"http://localhost:{port}/execute",
        port=port,
        container_id=container.id,
        image_name=image_tag,
        status=SkillStatus.BUILDING,
    )

    # Wait for healthy
    if wait_for_healthy(port):
        skill.status = SkillStatus.RUNNING
    else:
        container.stop(timeout=5)
        container.remove()
        skill.status = SkillStatus.FAILED
        raise RuntimeError(f"Skill '{spec.name}' failed to start within {config.SKILL_STARTUP_TIMEOUT}s")

    return skill


def wait_for_healthy(port: int) -> bool:
    """Poll /health until the container is ready."""
    deadline = time.time() + config.SKILL_STARTUP_TIMEOUT
    while time.time() < deadline:
        try:
            resp = httpx.get(f"http://localhost:{port}/health", timeout=2)
            if resp.status_code == 200:
                return True
        except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError):
            time.sleep(0.5)
    return False


def remove_skill(skill: Skill) -> None:
    """Stop and remove a skill's container and image."""
    client = docker.from_env()
    try:
        container = client.containers.get(skill.container_id)
        container.stop(timeout=5)
        container.remove()
    except docker.errors.NotFound:
        pass
    try:
        client.images.remove(skill.image_name, force=True)
    except docker.errors.ImageNotFound:
        pass
