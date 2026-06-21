# MCP REST API Server

A FastAPI gateway that wraps a local [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server and exposes its tools over a standard HTTP REST interface. This lets any HTTP client — including LLM agents, scripts, or other services — discover and invoke MCP tools without needing a native MCP client.

---

## Architecture

```
LLM Agent / HTTP Client
        │
        │  REST (HTTP)
        ▼
┌─────────────────────┐
│   rest_gateway.py   │  FastAPI app — exposes /tools and /invoke/{tool_name}
│   (MCPGateway)      │  Spawns mcp_server.py as a subprocess over stdio
└────────┬────────────┘
         │  MCP over stdio
         ▼
┌─────────────────────┐
│   mcp_server.py     │  MCP server — registers and runs tools
└─────────────────────┘
```

---

## Files

| File | Description |
|---|---|
| `mcp_server.py` | MCP server that registers all tools |
| `rest_gateway.py` | FastAPI app that bridges MCP ↔ REST |
| `requirements.txt` | Python dependencies |

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the gateway

```bash
uvicorn rest_gateway:app --reload --port 8000
```

The gateway automatically spawns `mcp_server.py` as a subprocess on startup.

---

## API Endpoints

### `GET /tools`
Returns a list of all tools exposed by the MCP server.

**Response:**
```json
{
  "tools": [
    {
      "name": "get_weather",
      "description": "Get real-time current weather for a city...",
      "input_schema": { "type": "object", "properties": { "city": { "type": "string" } } }
    }
  ]
}
```

---

### `POST /invoke/{tool_name}`
Invokes a specific tool with the provided arguments.

**Request body:**
```json
{
  "arguments": {
    "city": "London"
  }
}
```

**Response:**
```json
{
  "tool": "get_weather",
  "arguments": { "city": "London" },
  "result": "..."
}
```

**Error (tool not found):** `404`

---

## Available Tools

### `get_weather(city: str)`
Returns real-time weather for any city. Powered by [Open-Meteo](https://open-meteo.com/) — **no API key required**.

**Returns:** temperature, feels-like, humidity, wind speed, and condition.

```bash
curl -X POST http://localhost:8000/invoke/get_weather \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"city": "Tokyo"}}'
```

---

### `calculate(expression: str)`
Safely evaluates a mathematical expression.

Supports: `+`, `-`, `*`, `/`, `**` (power), `%`, parentheses.

```bash
curl -X POST http://localhost:8000/invoke/calculate \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"expression": "(24 * 3) + 5"}}'
```

---

### `normalize_name(name: str)`
Strips whitespace and title-cases a name string.

```bash
curl -X POST http://localhost:8000/invoke/normalize_name \
  -H "Content-Type: application/json" \
  -d '{"arguments": {"name": "  john doe  "}}'
```

---

## Interactive API Docs

Once the server is running, visit:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Adding a New Tool

1. Open `mcp_server.py`
2. Define a new function decorated with `@mcp.tool()`
3. Restart the gateway — the tool is automatically discovered and exposed via REST

```python
@mcp.tool()
def my_tool(input: str) -> dict:
    """Description of what this tool does."""
    return {"result": input.upper()}
```
