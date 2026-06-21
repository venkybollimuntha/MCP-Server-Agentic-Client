# MCP Tool Agent

A two-part system that exposes [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) tools over a REST API and drives them with a Groq-powered LLM agent.

```
mcp-rest-api-server/   ← FastAPI gateway + MCP tool server
mcp-client/            ← Groq LLM agent that calls the gateway
```

---

## How It Works

```
┌────────────────┐        HTTP REST         ┌──────────────────────────┐
│  mcp-client/   │  ─── GET /tools ──────►  │  mcp-rest-api-server/    │
│                │  ─── POST /invoke ──────► │  rest_gateway.py         │
│ agent_rest_    │  ◄─── JSON result ──────  │  (FastAPI)               │
│ mcp.py         │                           │         │  stdio          │
│                │                           │         ▼                 │
│ Groq LLM       │                           │  mcp_server.py           │
│ (llama-3.3-70b)│                           │  (MCP tools)             │
└────────────────┘                           └──────────────────────────┘
```

1. The **MCP server** (`mcp_server.py`) registers tools and communicates over stdio.
2. The **REST gateway** (`rest_gateway.py`) spawns the MCP server as a subprocess and exposes its tools via HTTP.
3. The **agent** (`agent_rest_mcp.py`) discovers tools from the gateway, passes them to Groq's LLM, and executes any tool calls in a loop until a final answer is reached.

---

## Repository Structure

```
├── mcp-rest-api-server/
│   ├── mcp_server.py       # MCP tool definitions
│   ├── rest_gateway.py     # FastAPI REST gateway
│   └── requirements.txt
│
├── mcp-client/
│   ├── agent_rest_mcp.py   # Groq LLM agent
│   └── .env                # GROQ_API_KEY
│
└── README.md
```

---

## Prerequisites

- Python 3.10+
- A Groq API key — sign up free and generate one at [console.groq.com/keys](https://console.groq.com/keys)

---

## Setup

### 1. Install dependencies

**Server:**
```bash
cd mcp-rest-api-server
pip install -r requirements.txt
```

**Client:**
```bash
cd mcp-client
pip install groq requests python-dotenv
```

### 2. Configure environment

Create a `.env` file inside `mcp-client/`:
```env
GROQ_API_KEY=your_groq_api_key_here
```

---

## Running

### Step 1 — Start the REST gateway

```bash
cd mcp-rest-api-server
uvicorn rest_gateway:app --reload --port 8000
```

This automatically spawns `mcp_server.py` as a subprocess. You should see:
```
[SERVER] MCP server started, waiting for requests...
```

### Step 2 — Run the agent

```bash
cd mcp-client
python agent_rest_mcp.py
```

```
Discovered tools: ['calculate', 'normalize_name', 'get_weather']
Agent ready. Type 'exit' to quit.

You: What's the weather in Paris?
Agent: The current weather in Paris, France is 22°C (feels like 21°C), partly cloudy...
```

---

## Available Tools

| Tool | Description |
|---|---|
| `get_weather` | Real-time weather for any city (via [Open-Meteo](https://open-meteo.com/), no API key needed) |
| `calculate` | Evaluate math expressions: `(24 * 3) + 5`, `2 ** 10` |
| `normalize_name` | Strip whitespace and title-case a name string |

### Adding a new tool

Open `mcp-rest-api-server/mcp_server.py` and add a decorated function:

```python
@mcp.tool()
def my_tool(input: str) -> dict:
    """What this tool does."""
    return {"result": input.upper()}
```

Restart the gateway — the tool is automatically discovered by the agent.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/tools` | List all available tools |
| `POST` | `/invoke/{tool_name}` | Invoke a tool with arguments |

**Interactive docs:** http://localhost:8000/docs

**Example:**
```bash
curl -X POST http://localhost:8000/invoke/get_weather \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"city": "Tokyo"}}'
```

---

## LLM Model

The agent uses **`llama-3.3-70b-versatile`** via the Groq API. To switch models, update the `model` field in `mcp-client/agent_rest_mcp.py`:

```python
resp = client.chat.completions.create(
    model="llama-3.3-70b-versatile",  # change here
    ...
)
```

Browse available models at [console.groq.com](https://console.groq.com/keys).
