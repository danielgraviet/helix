### Act 1: Skill Creation (CLI)
1. Generate a QR code for https://github.com/danielgraviet/helix
2. Now make me a QR code for https://www.blockchain.com/explorer/assets/btc
3. Create a chart showing revenue vs expenses over time @data.json

### Act 2: Self-Extension (CLI → Telegram)
4. Start the Telegram bot

### Act 3: Shared Intelligence (Telegram)
5. /skills
6. Create a chart showing revenue vs expenses over time for this data. [ {"month": "Jan", "revenue": 12400, "expenses": 9800, "users": 340}, {"month": "Mar", "revenue": 14200, "expenses": 11500, "users": 410}]
7. Build me a coin flip endpoint

### Act 4: Full Circle (CLI)
8. Flip a coin

---

## Talking Points

### Opening (before you start typing)
- "This is Helix — a self-extending AI agent. It doesn't come with pre-built tools. Instead, it writes code, packages it into Docker containers, and deploys microservices on the fly to solve whatever you throw at it."
- "Everything you're about to see is happening live. No pre-built skills, no mock data, no shortcuts."

### Step 1 — QR Code (while it builds)
- "I'm asking Helix to generate a QR code. It doesn't have that ability yet — watch what happens."
- "It just wrote a FastAPI service, built a Docker image, deployed a container, and called it. That skill didn't exist 20 seconds ago."
- *Open the /view URL* — "And here's the QR code, served from that container."

### Step 2 — Reuse (this should be instant)
- "Now I'm asking for another QR code. Watch — no rebuild this time."
- "It checked the registry, found the existing skill, and reused it. Instant."
- **Key point:** "This is the difference between a chatbot and an agent. It builds tools once and reuses them."

### Step 3 — Password Generator (while it builds)
- "Now something more complex — an interactive web app with a form."
- *Open the /view URL* — "This is a live web page served from a Docker container that was just created. Try changing the options."
- **Key point:** "Helix wrote the frontend, the backend, the Dockerfile, deployed it, and served it. All from one sentence."

### Step 4 — Data Visualization (while it builds)
- "I have a CSV file with a year of revenue data. I'm passing it to Helix with the @ symbol — it reads the file and injects it into the prompt."
- *Open the /view URL* — "Revenue vs expenses, 12 months, rendered as a chart."
- **Key point:** "The @ file reference means Helix can work with your local data without copy-pasting."

### Step 5 — Telegram Handoff (the wow moment)
- "Now here's where it gets interesting. I'm going to ask Helix to connect itself to Telegram."
- *Type the command, wait for confirmation*
- "Helix just spawned a Telegram bot in a background thread, sharing the same skill registry. It extended itself to a new interface — from one sentence."
- **Key point:** "This is self-extension. The agent didn't just create a tool — it created a new way to talk to itself."

### Step 6 — /skills on Telegram
- *Switch to phone/Telegram window*
- "Every skill I created in the CLI is already available here. Same registry, same containers."

### Step 7 — Telegram Creates a Skill
- "Telegram isn't just a viewer — it's a full client. I can create new skills from here too."
- "I'm passing inline data since there's no file system access from Telegram."

### Step 8 — Coin Flip from Telegram
- "One more — a simple coin flip endpoint, built entirely from Telegram."

### Step 9 — Full Circle (back to CLI)
- *Switch back to CLI*
- "Now watch this — I'm going to use the coin flip tool that Telegram just created."
- "It works. A skill created from Telegram, used in the CLI. The loop is complete."
- **Key point:** "Both interfaces create and consume from the same pool of skills. That's the architecture."

### Closing
- "Helix starts with zero capabilities. Every skill you saw was written, containerized, and deployed live by the agent. Skills persist, they're reusable, and they work across any interface."
- "The core idea: instead of building a tool for every use case, build an agent that builds its own tools."
- "Skills that evolve on demand."

---

## OBS Tips
- Have CLI and browser side-by-side so the audience sees the /view pages immediately
- Keep your phone screen visible (screen mirror or OBS phone capture) for the Telegram steps
- Pre-load the /view URLs in browser tabs during the build wait times so you can switch to them fast
- Have `data.json` open in your editor briefly when you mention the @ feature — shows it's a real file
