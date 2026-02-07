# Helix Roadmap — 48-Hour Hackathon Plan

## Goal

**Demo:** The agent receives a task, recognizes it lacks a skill, writes the code + Dockerfile, builds and deploys the container, then calls it to return a result — all live, end to end.

---

## Framework Recommendation: Claude API + Raw Tool Use

For a 48-hour hackathon focused on live skill creation, skip the heavy frameworks. Use **Anthropic's Claude API with native tool use** (or OpenAI function calling — same pattern). Reasons:

- **Zero framework overhead** — no learning curve, no abstractions fighting you.
- **Claude's tool_use is the orchestration loop** — define tools as JSON schemas, Claude decides when to call them. That *is* your orchestrator.
- **PydanticAI or LangGraph add complexity you don't need** when the core loop is: receive task → check registry → (maybe) synthesize skill → call skill.
- If you want structured output for code generation, just use Pydantic models to validate Claude's responses directly.

---

## Architecture (Simplified for 48h)

```
User prompt
    │
    ▼
┌──────────────┐
│  Orchestrator │  (Python CLI or simple FastAPI server)
│  Claude API   │  (tool_use for decision-making)
│  Tool Registry│  (in-memory dict → optional Redis)
└──────┬───────┘
       │
       ├── check_registry()  → existing skill? call it
       │
       └── synthesize_skill() → Skill Factory
                │
                ▼
        ┌───────────────┐
        │ Skill Factory  │  Generates code + Dockerfile
        │ docker-py SDK  │  Builds image, runs container
        └───────┬───────┘
                │
                ▼
        ┌───────────────┐
        │ Skill Container│  FastAPI on dynamic port
        │ /execute       │  POST — does the work
        │ /health        │  GET  — liveness check
        └───────────────┘
```

---

## Phase Breakdown

### Phase 0: Foundation (Hours 0–3)
**Goal:** Repo structure, dependencies, Docker network, and a running "hello world" orchestrator.

- [X] Initialize project structure:
  ```
  helix/
  ├── orchestrator/
  │   ├── main.py            # entry point
  │   ├── agent.py           # Claude API loop with tool definitions
  │   ├── registry.py        # tool registry (in-memory dict)
  │   └── config.py          # env vars, constants
  ├── skill_factory/
  │   ├── factory.py         # code generation + docker build logic
  │   ├── templates/         # base skill templates
  │   │   └── fastapi_skill/
  │   │       ├── main.py.j2       # Jinja2 template for skill code
  │   │       └── Dockerfile.j2    # Jinja2 template for Dockerfile
  │   └── port_manager.py    # find/allocate open ports
  ├── requirements.txt
  ├── docker-compose.yml     # optional, for Redis if used
  └── plan.md
  ```
- [X] Install core dependencies: `anthropic`, `docker`, `fastapi`, `uvicorn`, `jinja2`, `httpx`
- [X] Create Docker bridge network: `docker network create agent-net`
- [X] Verify `docker-py` can build and run a container programmatically (simple test)

### Phase 1: Skill Template + Factory (Hours 3–8)
**Goal:** The Skill Factory can take a description and produce a running container with a `/execute` endpoint.

- [X] Build the **FastAPI skill template** (Jinja2):
  - Accepts a `skill_name`, `description`, and `execute_logic` block
  - Produces a working `main.py` + `Dockerfile`
  - Template includes `/execute` (POST) and `/health` (GET)
- [X] Build `factory.py`:
  - Takes skill spec (name, description, code logic) as input
  - Renders the Jinja2 templates into a temp directory
  - Uses `docker.from_env()` to build image and run container
  - Connects container to `agent-net`
  - Returns the container's endpoint URL
- [X] Build `port_manager.py`:
  - Simple approach: start at port 9001, increment, check if free with `socket`
- [X] **Test manually:** Call the factory with a hardcoded spec, verify the container comes up and responds to `/execute`

### Phase 2: Tool Registry (Hours 8–10)
**Goal:** The orchestrator can store, discover, and route to skills.

- [X] Build `registry.py`:
  - `register(skill_name, endpoint_url, description, input_schema)` — adds a skill
  - `lookup(skill_name)` — returns endpoint or None
  - `list_skills()` — returns all registered skills with descriptions
  - Start with an in-memory `dict`. Skills are now saved to a build directory for future debugging.
- [X] After the factory deploys a container, it auto-registers in the registry
- [X] Add a health-check loop: on startup, ping `/health` on all registered skills, prune dead ones

### Phase 3: Orchestrator Agent Loop (Hours 10–18)
**Goal:** Claude receives a user prompt, decides if a skill exists or needs creation, and acts accordingly.

- [X] Define Claude tools (these are the JSON tool schemas Claude can call):
  - `list_available_skills` — returns registry contents
  - `call_skill` — calls a skill's `/execute` endpoint with given params
  - `create_new_skill` — triggers the Skill Factory with a spec
- [X] Build the **agent loop** in `agent.py`:
  ```
  while True:
      response = claude.messages.create(tools=tools, ...)
      if response.stop_reason == "tool_use":
          execute the tool call
          feed result back to Claude
      elif response.stop_reason == "end_turn":
          return final answer to user
  ```
- [X] The critical prompt engineering:
  - System prompt tells Claude it's an orchestrator that can create new microservice skills
  - When Claude calls `create_new_skill`, it provides: skill name, description, and the Python code for the `/execute` handler
  - Claude writes the *actual business logic* — the factory just wraps it in the template
- [X] **Test end to end:** Ask "What time is it in Tokyo?" → Claude creates a `timezone_converter` skill → container deploys → Claude calls it → returns answer

### Phase 4: Hardening + Polish (Hours 18–24)
**Goal:** Make the demo reliable and visually impressive.

- [X] Add **timeout guards** to Docker builds/runs (prevent infinite loops)
- [X] Add **container cleanup**: stop/remove containers that haven't been called in N minutes
- [X] Add **build error handling**: if the generated code fails to build, feed the error back to Claude and let it retry (self-healing loop)
- [X] Add **logging/output** so the demo is visible:
  - Print each step: "Checking registry...", "No skill found, creating...", "Building Docker image...", "Container running on port 9003", "Calling skill...", "Result: ..."
  - Use `rich` library for colored terminal output if time allows
- [X] Test with 2-3 different skill types:
  - A math/utility skill (simple, fast to verify)
  - A web scraping skill (shows real-world value)
  - A data processing skill (CSV analysis, etc.)

### Phase 5: Demo Prep (Hours 24–30, if time)
**Goal:** Stretch goals that elevate the demo.

- [ ] **Secret Vault (simplified):** Environment variable injection via `docker-py`'s `environment` param — skip the web form, just pass secrets from a local `.env` file
- [ ] **Skill chaining:** Claude calls one skill, feeds its output into another
- [ ] **Simple web UI:** A Streamlit or Gradio chat interface that shows the conversation + a sidebar listing active skill containers
- [ ] **Pre-seed a couple skills** so the demo starts fast, then create a new one live
- [ ] **Interface Handoff to Telegram** Can I have Helix create a webhook/interaction with telegram so I can communciate with through there?

---

## Key Risks + Mitigations

| Risk | Mitigation |
|---|---|
| Claude generates broken code | Feed Docker build errors back to Claude for retry (max 3 attempts) |
| Port conflicts | Use `socket` to probe before allocating; keep a port ledger |
| Docker build is slow during demo | Pre-pull base images (`python:3.12-slim`). Cache pip installs in Dockerfile template |
| Container doesn't start | Add a health-check poll loop (retry `/health` for 10s before failing) |
| Scope creep | The demo is ONE flow: no skill → create skill → call skill. Everything else is optional |

---

## Demo Script (What to Show)

1. Start the orchestrator (terminal)
2. Type: *"Convert this CSV data to a bar chart"* (or similar)
3. Watch the orchestrator:
   - Check registry → no `data_visualizer` skill
   - Claude writes the skill code
   - Docker image builds (10-20 seconds)
   - Container starts on port 9001
   - Skill registered
   - Claude calls `/execute` with the data
   - Result returned
4. Type a follow-up that reuses the same skill → instant response (no rebuild)
5. Type a new request requiring a *different* skill → watch it create a second container

**The "wow moment":** The agent didn't have the capability 30 seconds ago. Now it does. And it's persistent.

---

## Quick Start Commands

```bash
# Create project
mkdir -p orchestrator skill_factory/templates/fastapi_skill
python -m venv .venv && source .venv/bin/activate
pip install anthropic docker fastapi uvicorn jinja2 httpx rich

# Docker setup
docker network create agent-net
docker pull python:3.12-slim  # pre-cache base image

# Set API key
export ANTHROPIC_API_KEY="your-key-here"

# Run
python orchestrator/main.py
```