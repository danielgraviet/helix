import json

import anthropic
import httpx
from rich.console import Console

import config
from models.skill import SkillSpec
from orchestrator.registry import SkillRegistry
from skill_factory.factory import build_and_run

console = Console()

# --- Tool definitions (JSON schemas Claude can call) ---

TOOLS = [
    {
        "name": "list_available_skills",
        "description": "List all skills currently registered and available to call.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "call_skill",
        "description": "Call an existing skill's /execute endpoint with a JSON payload.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "The name of the skill to call.",
                },
                "payload": {
                    "type": "object",
                    "description": "The JSON body to send to the skill's /execute endpoint.",
                },
            },
            "required": ["skill_name", "payload"],
        },
    },
    {
        "name": "create_new_skill",
        "description": (
            "Create a new skill as a Docker microservice. "
            "You write the Python code for the /execute handler. "
            "The code receives a 'body' dict (parsed JSON from the request) "
            "and must return a dict response. "
            "Example: 'result = body[\"x\"] * 2\\nreturn {\"result\": result}'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Unique snake_case name for the skill (e.g. 'csv_analyzer').",
                },
                "description": {
                    "type": "string",
                    "description": "What the skill does.",
                },
                "execute_code": {
                    "type": "string",
                    "description": (
                        "Python code for the /execute handler body. "
                        "Has access to 'body' (dict from request JSON). "
                        "Must return a dict. Use \\n for newlines."
                    ),
                },
                "view_post_code": {
                    "type": "string",
                    "description": (
                        "Python code for handling form POST to /view. "
                        "Has access to 'form_data' (dict from form submission), '_state', and '_viewable_html'. "
                        "Should update _state, regenerate _viewable_html, and return HTMLResponse(_viewable_html). "
                        "Only needed for interactive/stateful web pages."
                    ),
                },
                "dependencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Extra pip packages needed (e.g. ['requests', 'pandas']).",
                },
            },
            "required": ["name", "description", "execute_code"],
        },
    },
]

SYSTEM_PROMPT = """\
You are an orchestrator agent that can create and use microservice skills.

Each skill is a Docker container with a /execute endpoint. You can:
1. List existing skills to see what's available.
2. Call a skill by name with a JSON payload.
3. Create a new skill if none exists for the task.

When creating a skill:
- Write clean Python for the execute_code field.
- The code receives 'body' (a dict from the request JSON) and must return a dict.
- Include any pip dependencies the code needs.
- Keep skills focused on a single capability.
- NEVER start a new HTTP server inside execute_code. The container already runs a web server.

If the task involves viewable content (HTML, a webpage, a chart):
- Store the HTML in the _viewable_html global: _viewable_html = "<html>..."
- Do NOT include 'global' declarations in your code — they are already declared in the handlers.
- Return a dict with the result status. The user can view the content at the skill's /view URL.
- The view_url is returned when the skill is created. Use that URL — do not invent your own.
- IMPORTANT: After creating a viewable skill, you MUST call it with call_skill before giving the user the view URL. The /view page is empty until /execute runs and populates the content.

For interactive/stateful web pages (forms, to-do lists, counters, etc.):
- Use _state (a dict) to store persistent data across requests.
- In execute_code: initialize _state with default values and render the initial HTML into _viewable_html.
- Provide view_post_code to handle form submissions. It receives 'form_data' (dict from the form).
  Update _state based on form_data, regenerate _viewable_html, and return HTMLResponse(_viewable_html).
- HTML forms should POST to "/view" with action="/view" method="post".
- Use name attributes on form inputs so they appear in form_data.

Always check available skills before creating a new one. Reuse existing skills when possible.\
"""


# --- Tool handlers ---

def handle_list_skills(registry: SkillRegistry, **kwargs) -> str:
    skills = registry.list_skills()
    if not skills:
        return "No skills registered yet."
    return json.dumps(skills, indent=2)


def handle_call_skill(registry: SkillRegistry, skill_name: str, payload: dict) -> str:
    skill = registry.lookup(skill_name)
    if skill is None:
        return json.dumps({"error": f"Skill '{skill_name}' not found in registry."})

    try:
        resp = httpx.post(skill.endpoint, json=payload, timeout=30)
        return resp.text
    except Exception as e:
        return json.dumps({"error": f"Failed to call skill: {str(e)}"})


def handle_create_skill(registry: SkillRegistry, name: str, description: str, execute_code: str, view_post_code: str | None = None, dependencies: list[str] | None = None) -> str:
    # Check if skill already exists
    if registry.lookup(name):
        return json.dumps({"error": f"Skill '{name}' already exists."})

    spec_kwargs = dict(
        name=name,
        description=description,
        execute_code=execute_code,
        dependencies=dependencies or [],
    )
    if view_post_code:
        spec_kwargs["view_post_code"] = view_post_code

    spec = SkillSpec(**spec_kwargs)

    for attempt in range(1, config.MAX_BUILD_RETRIES + 1):
        try:
            console.print(f"[yellow]Building skill '{name}' (attempt {attempt}/{config.MAX_BUILD_RETRIES})...[/yellow]")
            skill = build_and_run(spec)
            registry.register(skill)
            console.print(f"[green]Skill '{name}' deployed on port {skill.port}[/green]")
            view_url = f"http://localhost:{skill.port}/view"
            return json.dumps({"status": "created", "name": name, "endpoint": skill.endpoint, "view_url": view_url})
        except Exception as e:
            error_msg = str(e)
            console.print(f"[red]Build attempt {attempt} failed: {error_msg[:200]}[/red]")
            if attempt == config.MAX_BUILD_RETRIES:
                return json.dumps({
                    "error": f"Failed after {config.MAX_BUILD_RETRIES} attempts. Last error: {error_msg}",
                    "hint": "Try simpler code, check dependencies, or use a different approach.",
                })


TOOL_HANDLERS = {
    "list_available_skills": handle_list_skills,
    "call_skill": handle_call_skill,
    "create_new_skill": handle_create_skill,
}


# --- Agent loop ---

def run_agent(user_message: str, registry: SkillRegistry) -> str:
    """Send a user message through the agent loop. Returns the final text response."""
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    messages = [{"role": "user", "content": user_message}]

    while True:
        console.print("[dim]Thinking...[/dim]")

        response = client.messages.create(
            model=config.MODEL,
            max_tokens=config.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Collect text and tool use blocks from the response
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        # If Claude is done (no more tool calls), return the text
        if response.stop_reason == "end_turn":
            text_parts = [block.text for block in assistant_content if block.type == "text"]
            return "\n".join(text_parts)

        # Process tool calls
        tool_results = []
        for block in assistant_content:
            if block.type != "tool_use":
                continue

            tool_name = block.name
            tool_input = block.input
            console.print(f"[cyan]Calling tool: {tool_name}[/cyan]")

            handler = TOOL_HANDLERS.get(tool_name)
            if handler is None:
                result = json.dumps({"error": f"Unknown tool: {tool_name}"})
            else:
                result = handler(registry=registry, **tool_input)

            console.print(f"[dim]Tool result: {result[:200]}[/dim]")

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})
