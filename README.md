# 🤖 Customer Support AI – Multi-Agent System

A Generative AI–powered Multi-Agent System that lets John (customer support executive)
query **structured customer data** (SQLite) and **unstructured policy documents** (PDFs)
through a single natural-language chat interface.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit UI  (app.py)                 │
└────────────────────────┬────────────────────────────────┘
                         │ query
                         ▼
┌─────────────────────────────────────────────────────────┐
│            LangGraph Orchestration  (agents/graph.py)    │
│                                                          │
│   ┌─────────────┐                                        │
│   │  Supervisor │  classifies: sql / rag / both / general│
│   └──────┬──────┘                                        │
│          │                                               │
│   ┌──────▼──────┐   ┌──────────────┐                    │
│   │  SQL Agent  │   │   RAG Agent  │                    │
│   │  (NL→SQL)   │   │ (embeddings) │                    │
│   └──────┬──────┘   └──────┬───────┘                    │
│          └────────┬─────────┘                            │
│                   ▼                                      │
│            ┌────────────┐                                │
│            │Synthesizer │  Claude Sonnet → final answer  │
│            └────────────┘                                │
└─────────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
┌─────────────────┐       ┌──────────────────────┐
│  SQLite DB      │       │  ChromaDB (vector)   │
│  customers      │       │  + sentence-          │
│  support_tickets│       │    transformers       │
└─────────────────┘       └──────────────────────┘

Optional:
┌─────────────────────────────────────────────────────────┐
│          FastAPI MCP Tool Server  (mcp_server.py)        │
│  POST /tools/query_customer_data                         │
│  POST /tools/search_policy_docs                          │
│  POST /tools/ingest_document                             │
└─────────────────────────────────────────────────────────┘
```

### Components
| Component | Technology | Purpose |
|-----------|-----------|---------|
| LLM | Claude Sonnet (Anthropic) | NL understanding, SQL generation, synthesis |
| Embeddings | `sentence-transformers` (MiniLM-L6-v2) | Local, free, no API key needed |
| Vector DB | ChromaDB (persistent) | Semantic search over PDFs |
| Structured DB | SQLite | Customer profiles + ticket history |
| Agent framework | LangGraph | Multi-agent state machine |
| MCP Server | FastAPI + Uvicorn | Optional tool-server layer |
| UI | Streamlit | Chat + PDF upload interface |

---

## Prerequisites

- Python 3.10+
- An **Anthropic API key** — get one at https://console.anthropic.com

---

## Quick Start

### 1. Clone / unzip the project

```bash
cd customer-support-ai
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> First install downloads the `all-MiniLM-L6-v2` embedding model (~90 MB). This is a one-time download.

### 4. Set your API key

```bash
cp .env.example .env
# Edit .env and replace with your actual key:
#   ANTHROPIC_API_KEY=sk-ant-...
```

### 5. Set up the database

```bash
python setup_data.py
```

This creates `data/customers.db` with 10 synthetic customers and 19 support tickets.

### 6. Run the Streamlit app

```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## Using the Application

### Chat Interface
Type any question in the chat box. The Supervisor agent automatically routes it:

| Query type | Example | Agent used |
|-----------|---------|-----------|
| Customer data | "Give me Ema's profile and tickets" | 📊 SQL Agent |
| Policy docs | "What is the refund policy?" | 📄 RAG Agent |
| Both | "Does Ema qualify for a refund per policy?" | Both |
| General | "How should I handle angry customers?" | Synthesizer |

### Uploading Policy Documents
1. Click **Browse files** in the sidebar.
2. Select one or more PDF files (company policies, procedures, etc.).
3. Wait for the green ✅ confirmation — chunks are stored in ChromaDB.
4. Ask questions about the document content.

**Tip:** You can use any publicly available policy PDFs, for example:
- Apple Media Services Terms: https://www.apple.com/legal/internet-services/itunes/
- Any company's publicly published refund/return/privacy policy PDF

### Quick Queries (Sidebar)
Click pre-built buttons to try common queries instantly.

### Agent Trace
Expand the **🔍 Agent trace** under any response to see:
- Which agent(s) handled the query
- The SQL generated (for database queries)
- Routing decisions

---

## Running the MCP Tool Server (Optional)

The MCP server exposes all tools as HTTP endpoints, following the Model Context Protocol pattern.

```bash
# In a separate terminal (with venv active):
python mcp_server.py
```

Server runs at **http://localhost:8000**

### Available endpoints

```
GET  /tools                       # List all available tools
GET  /health                      # Health check
POST /tools/query_customer_data   # {"query": "..."}
POST /tools/search_policy_docs    # {"query": "..."}
POST /tools/ingest_document       # {"filename": "...", "file_b64": "..."}
GET  /tools/list_documents        # List indexed documents
GET  /tools/get_db_schema         # Show DB schema
```

Interactive API docs: **http://localhost:8000/docs**

---

## Sample Customer Data

| ID | Name | Email | Phone | Plan | Join Date | Status | Address | Total Spend |
|----|------|-------|-------|------|-----------|--------|---------|-------------|
| 1 | Ema Johnson | ema.johnson@email.com | 555-1234 | Premium | 2022-03-15 | Active | 123 Main St, NY | $2,450.00 |
| 2 | Robert Chen | robert.chen@email.com | 555-2345 | Basic | 2023-01-10 | Active | 456 Oak Ave, CA | $890.50 |
| 3 | Alice Brown | alice.brown@email.com | 555-3456 | Premium | 2021-11-20 | Inactive | 789 Pine Rd, TX | $5,200.75 |
| 4 | Michael Davis | michael.davis@email.com | 555-4567 | Enterprise | 2020-06-05 | Active | 321 Elm St, FL | $12,000.00 |
| 5 | Sarah Wilson | sarah.wilson@email.com | 555-5678 | Basic | 2023-08-22 | Active | 654 Maple Dr, WA | $345.25 |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

## Sample Support Ticket Data

| ID | Customer ID | Date | Category | Issue | Status | Priority | Resolution |
|----|-------------|------|----------|-------|--------|----------|------------|
| 1 | 1 | 2023-05-10 | Billing | Duplicate charge on monthly subscription | Resolved | High | Refund issued within 3 business days |
| 2 | 1 | 2023-08-22 | Technical | Login issues after password reset | Resolved | Medium | Account unlocked, password reset link sent |
| 3 | 1 | 2024-01-15 | Product | Feature not working on mobile app | In Progress | Low | Engineering team investigating |
| 4 | 1 | 2024-03-01 | Billing | Request for invoice for tax purposes | Resolved | Low | Invoice sent via email |
| 5 | 2 | 2023-09-05 | Technical | API integration errors | Resolved | High | Configuration guide provided |
| ... | ... | ... | ... | ... | ... | ... | ... |

---

## Example Queries to Try

```
"Give me a quick overview of customer Ema's profile and past support ticket details."
"List all customers on the Enterprise plan."
"Show me all unresolved high-priority tickets."
"What is the current refund policy?"        ← requires PDF upload
"Which customers have billing issues?"
"Who are the top 3 spenders?"
"Does Michael Davis have any open tickets?"
"Summarize the data retention policy."      ← requires PDF upload
```

---

## Project Structure

```
customer-support-ai/
├── app.py              # Streamlit chat UI
├── mcp_server.py       # FastAPI MCP tool server
├── config.py           # Config (paths, model names)
├── setup_data.py       # DB bootstrap script
├── requirements.txt
├── .env.example
├── agents/
│   └── graph.py        # LangGraph multi-agent state machine
├── tools/
│   ├── sql_tools.py    # NL → SQL → SQLite
│   └── rag_tools.py    # PDF ingest + ChromaDB search
└── data/               # Created at runtime
    ├── customers.db    # SQLite
    └── chroma_db/      # Vector store
```

---

## Troubleshooting

**`ANTHROPIC_API_KEY` error**
→ Make sure `.env` exists with your key, or export it: `export ANTHROPIC_API_KEY=sk-ant-...`

**Embedding model slow on first run**
→ The model downloads ~90 MB once. Subsequent runs are instant.

**PDF text extraction returns empty**
→ Some scanned PDFs have no embedded text. Use OCR-processed PDFs.

**ChromaDB version conflict**
→ Run `pip install chromadb --upgrade`

**Port 8501 already in use**
→ `streamlit run app.py --server.port 8502`
