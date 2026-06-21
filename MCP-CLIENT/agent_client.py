import os
import json
import requests
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

BASE_URL = "http://localhost:8000"   # your MCP REST gateway

# ----------------------------
# REST wrappers
# ----------------------------
def fetch_tools():
    r = requests.get(f"{BASE_URL}/tools", timeout=20)
    r.raise_for_status()
    return r.json()["tools"]

def invoke_tool(tool_name: str, arguments: dict):
    r = requests.post(
        f"{BASE_URL}/invoke/{tool_name}",
        json={"arguments": arguments},
        timeout=30
    )
    r.raise_for_status()
    return r.json()

# ----------------------------
# Build Groq tool schemas from /tools
# ----------------------------
def build_groq_tools(tools_from_rest):
    groq_tools = []
    for t in tools_from_rest:
        groq_tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description") or "",
                "parameters": t.get("input_schema") or {
                    "type": "object",
                    "properties": {}
                }
            }
        })
    return groq_tools

# ----------------------------
# Agent loop
# ----------------------------
def run_agent(user_input: str, tools_schema):
    messages = [
        {"role": "system", "content": "You are a helpful agent. Use available tools when needed."},
        {"role": "user", "content": user_input}
    ]

    for _ in range(8):
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            tools=tools_schema,
            tool_choice="auto",
            temperature=0
        )
        msg = resp.choices[0].message

        if msg.tool_calls:
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in msg.tool_calls
                ]
            })

            for tc in msg.tool_calls:
                tool_name = tc.function.name
                tool_args = json.loads(tc.function.arguments or "{}")

                tool_result = invoke_tool(tool_name, tool_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result)
                })
            continue

        return msg.content or "(no response)"

    return "Max steps reached."

if __name__ == "__main__":
    # 1) Discover tools from MCP REST server
    tools = fetch_tools()
    print("Discovered tools:", [t["name"] for t in tools])

    # 2) Convert to Groq tool schema
    tool_schema = build_groq_tools(tools)

    print("Agent ready. Type 'exit' to quit.\n")
    while True:
        q = input("You: ").strip()
        if q.lower() in {"exit", "quit"}:
            break

        ans = run_agent(q, tool_schema)
        print(f"Agent: {ans}\n")
