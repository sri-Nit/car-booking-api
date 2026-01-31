from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

app = FastAPI()
mcp = FastApiMCP(app)

mcp.import_tools_from_openapi("http://127.0.0.1:8000/openapi.json")

mcp.mount()
mcp.setup_server()
