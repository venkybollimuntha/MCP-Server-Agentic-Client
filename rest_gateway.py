import asyncio
from groq import Groq
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


app = FastAPI(title="MCP REST API Gateway")

class InvokeBody(BaseModel):
    arguments: Dict[str, Any] = {}

class MCPGateway:
    """
    Gateway that manages a persistent MCP (Model Context Protocol) client session.

    Spawns a local MCP server subprocess (`mcp_server.py`) over stdio and exposes
    its tools via a FastAPI REST interface.
    """

    def __init__(self):
        self.session = None
        self.read = None
        self.write = None
        self.ctx = None
        self.srv = None
        self.tools_cache = None
        
    
    async def start(self):
        """Launch the MCP server subprocess and establish the client session."""
        self.srv = StdioServerParameters(command="python", args=["mcp_server.py"])
        self.ctx = stdio_client(self.srv)
        self.read, self.write = await self.ctx.__aenter__()
        self.session = ClientSession(self.read, self.write)
        await self.session.__aenter__()
        await self.session.initialize()
        await self.refresh_tools()
        
    async def refresh_tools(self):
        """Fetch available tools from the MCP server and update the local cache."""
        tools_list = await self.session.list_tools()
        self.tools_cache = {t.name : t for t in tools_list.tools}
        
        
    async def stop(self):
        """Gracefully shut down the MCP session and subprocess."""
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self.ctx:
            await self.ctx.__aexit__(None, None, None)
            
gateway = MCPGateway()

@app.on_event("startup")
async def startup_event():
    await gateway.start()

@app.on_event("shutdown")
async def shutdown_event():
    await gateway.stop()
    
    
@app.get("/tools", summary="List available tools", description="Returns all tools exposed by the MCP server.")
async def get_tools():
    out = []
    for name, t in gateway.tools_cache.items():
        out.append({
            "name": name,
            "description": t.description,
            "input_schema": t.inputSchema
        })
    return {"tools": out}

@app.post("/invoke/{tool_name}", summary="Invoke a tool", description="Invokes a specific tool with the provided arguments.")
async def invoke_tool(tool_name: str, body: InvokeBody):
    if tool_name not in gateway.tools_cache:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    
    try:
        result = await gateway.session.call_tool(tool_name, body.arguments)
        
        # normalize MCP result content for REST response
        chunks = []
        if hasattr(result, "content") and result.content:
            for c in result.content:
                if hasattr(c, "text") and c.text:
                    chunks.append(c.text)
                else:
                    chunks.append(str(c))
                    
        return {
           "tool": tool_name,
           "arguments": body.arguments,
           "result": "".join(chunks) if chunks else str(result)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))