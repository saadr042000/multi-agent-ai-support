"""
MCP Tool Server (FastAPI)
==========================
Exposes customer-support tools as HTTP endpoints following the
Model Context Protocol pattern. Run separately:

    python mcp_server.py

Endpoints:
  GET  /tools                      – list available tools
  POST /tools/query_customer_data  – NL → SQL → results
  POST /tools/search_policy_docs   – semantic search over vector DB
  POST /tools/ingest_document      – ingest a PDF (base64 payload)
  GET  /health                     – health check
"""
import base64
import os
import sys
import tempfile

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(__file__))

from tools.sql_tools import nl_to_sql_and_run, get_db_schema
from tools.rag_tools import search_documents, ingest_pdf, list_documents, delete_document

# ── App setup ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Customer Support MCP Tool Server",
    description="Multi-agent tool server for structured + unstructured data access",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request/Response models ────────────────────────────────────────────────────

class NLQueryRequest(BaseModel):
    query: str

class IngestRequest(BaseModel):
    filename: str
    file_b64: str           # base64-encoded PDF bytes

class DeleteRequest(BaseModel):
    filename: str

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "Customer Support MCP Server"}


@app.get("/tools")
def list_tools():
    """MCP-style tool manifest."""
    return {
        "tools": [
            {
                "name": "query_customer_data",
                "description": "Query structured customer profiles and support tickets using natural language.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Natural-language question about customers or tickets"}},
                    "required": ["query"],
                },
            },
            {
                "name": "search_policy_docs",
                "description": "Semantically search uploaded policy and procedure PDF documents.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Question about company policies or procedures"}},
                    "required": ["query"],
                },
            },
            {
                "name": "ingest_document",
                "description": "Upload and index a PDF document into the knowledge base.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "file_b64": {"type": "string", "description": "Base64-encoded PDF content"},
                    },
                    "required": ["filename", "file_b64"],
                },
            },
            {
                "name": "list_documents",
                "description": "List all policy documents currently indexed in the knowledge base.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_db_schema",
                "description": "Return the SQL database schema (for debugging/exploration).",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]
    }


@app.post("/tools/query_customer_data")
def query_customer_data(req: NLQueryRequest):
    try:
        result = nl_to_sql_and_run(req.query)
        return {"tool": "query_customer_data", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/search_policy_docs")
def search_policy_docs(req: NLQueryRequest):
    try:
        result = search_documents(req.query)
        return {"tool": "search_policy_docs", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/ingest_document")
def ingest_document(req: IngestRequest):
    try:
        pdf_bytes = base64.b64decode(req.file_b64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name
        result = ingest_pdf(tmp_path, req.filename)
        os.unlink(tmp_path)
        return {"tool": "ingest_document", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/list_documents")
def list_docs():
    return {"tool": "list_documents", "result": list_documents()}


@app.post("/tools/delete_document")
def delete_doc(req: DeleteRequest):
    return {"tool": "delete_document", "result": delete_document(req.filename)}


@app.get("/tools/get_db_schema")
def db_schema():
    return {"tool": "get_db_schema", "result": get_db_schema()}


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("mcp_server:app", host="0.0.0.0", port=8000, reload=False)
