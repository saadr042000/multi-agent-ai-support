"""
Customer Support AI Assistant – Streamlit UI
============================================
Main interface for John to query customer data and policy documents.
"""
import os
import sys
import tempfile

import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

# ── Page config (must be first Streamlit call) ─────────────────────────────────
st.set_page_config(
    page_title="Support AI Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auto-bootstrap database if missing ────────────────────────────────────────
from config import DB_PATH, ANTHROPIC_API_KEY
if not os.path.exists(DB_PATH):
    with st.spinner("🔧 First run: creating sample database…"):
        from setup_data import create_database
        create_database()

# ── Validate API key ──────────────────────────────────────────────────────────
if not ANTHROPIC_API_KEY:
    st.error(
        "⚠️ **ANTHROPIC_API_KEY** not found.\n\n"
        "Create a `.env` file with `ANTHROPIC_API_KEY=sk-ant-...` and restart."
    )
    st.stop()

from agents.graph import create_graph as create_agent_graph
from tools.rag_tools import ingest_pdf, list_documents, delete_document

# ── Session state initialisation ──────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "graph" not in st.session_state:
    with st.spinner("⚙️ Loading AI agents…"):
        st.session_state.graph = create_agent_graph()

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .agent-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-right: 4px;
    }
    .sql-badge  { background:#e8f4fd; color:#1a6ea8; border:1px solid #b3d7f0; }
    .rag-badge  { background:#e8fdf4; color:#1a8a55; border:1px solid #b3f0d1; }
    .info-card  { background:#f8f9fa; border-radius:8px; padding:12px 16px; border:1px solid #dee2e6; }
    .trace-box  { border-radius:6px; padding:8px 12px;
                  border-left:3px solid #ffc107; font-size:0.82rem; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/bot.png", width=56)
    st.title("Support AI")
    st.caption("Multi-Agent Customer Support System")
    st.divider()

    # ── Document management ──────────────────────────────────────────────────
    st.subheader("📁 Policy Documents")
    uploaded = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload company policy PDFs to enable the RAG agent.",
    )
    if uploaded:
        for uf in uploaded:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uf.getvalue())
                tmp_path = tmp.name
            with st.spinner(f"Processing {uf.name}…"):
                msg = ingest_pdf(tmp_path, uf.name)
                os.unlink(tmp_path)
            st.success(msg)

    docs = list_documents()
    if docs:
        st.markdown("**Indexed documents:**")
        for doc in docs:
            col1, col2 = st.columns([4, 1])
            col1.markdown(f"📄 `{doc}`")
            if col2.button("🗑️", key=f"del_{doc}", help=f"Remove {doc}"):
                delete_document(doc)
                st.rerun()
    else:
        st.info("No documents indexed yet.")

    st.divider()

    # ── Quick queries ────────────────────────────────────────────────────────
    st.subheader("💡 Quick Queries")

    QUICK = [
        ("👤 Ema's full profile",         "Give me a full overview of customer Ema's profile and all past support ticket details."),
        ("📋 All active customers",        "List all active customers with their plan type and total spend."),
        ("🎫 Open/In-Progress tickets",    "Show me all open or in-progress support tickets with customer names."),
        ("💰 Top spenders",               "Who are the top 5 customers by total spend?"),
        ("🔴 High-priority tickets",      "List all high-priority support tickets with customer name and resolution status."),
        ("📜 Refund policy",              "What is the company refund policy?"),
        ("🔒 Privacy / data policy",      "What does the privacy or data retention policy say?"),
        ("📦 Return policy",              "Explain the return and exchange policy."),
    ]

    for label, query in QUICK:
        if st.button(label, use_container_width=True):
            st.session_state.pending_query = query

    st.divider()
    if st.button("🧹 Clear chat history", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

    st.markdown(
        "<div style='font-size:0.75rem;color:#888;text-align:center'>"
        "SQL Agent · RAG Agent · Claude Sonnet"
        "</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CHAT AREA
# ─────────────────────────────────────────────────────────────────────────────
st.title("🤖 Customer Support AI Assistant")
st.caption(
    "Ask anything about **customers & tickets** (SQL Agent) "
    "or **company policies** (RAG Agent). "
    "Upload PDFs in the sidebar to activate the knowledge base."
)

# Agent legend
col1, col2, col3 = st.columns(3)
col1.markdown('<span class="agent-badge sql-badge">📊 SQL Agent</span> Structured customer data', unsafe_allow_html=True)
col2.markdown('<span class="agent-badge rag-badge">📄 RAG Agent</span> Policy documents', unsafe_allow_html=True)
col3.markdown("🧭 **Supervisor** routes each query automatically")

st.divider()

# ── Render chat history ───────────────────────────────────────────────────────
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("trace"):
            with st.expander("🔍 Agent trace", expanded=False):
                for t in msg["trace"]:
                    st.markdown(f'<div class="trace-box">{t}</div>', unsafe_allow_html=True)
            badges = ""
            if msg.get("used_sql"):
                badges += '<span class="agent-badge sql-badge">📊 SQL Agent</span>'
            if msg.get("used_rag"):
                badges += '<span class="agent-badge rag-badge">📄 RAG Agent</span>'
            if badges:
                st.markdown(badges, unsafe_allow_html=True)


# ── Query handler ─────────────────────────────────────────────────────────────
def handle_query(prompt: str):
    """Run the LangGraph pipeline and render the response."""
    # Add user message
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare chat history for context (exclude current message)
    history_for_llm = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.chat_history[:-1]
        if m["role"] in ("user", "assistant")
    ]

    initial_state = {
        "query": prompt,
        "query_type": None,
        "sql_data": None,
        "rag_data": None,
        "final_response": "",
        "chat_history": history_for_llm,
        "agent_trace": [],
    }

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            result = st.session_state.graph.invoke(initial_state)

        response = result["final_response"]
        trace    = result.get("agent_trace", [])
        used_sql = result.get("sql_data") is not None
        used_rag = result.get("rag_data") is not None and not (
            result.get("rag_data", "").startswith("NO_DOCUMENTS")
        )

        st.markdown(response)

        if trace:
            with st.expander("🔍 Agent trace", expanded=False):
                for t in trace:
                    st.markdown(f'<div class="trace-box">{t}</div>', unsafe_allow_html=True)

        badges = ""
        if used_sql:
            badges += '<span class="agent-badge sql-badge">📊 SQL Agent</span>'
        if used_rag:
            badges += '<span class="agent-badge rag-badge">📄 RAG Agent</span>'
        if badges:
            st.markdown(badges, unsafe_allow_html=True)

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": response,
        "trace": trace,
        "used_sql": used_sql,
        "used_rag": used_rag,
    })


# ── Handle pending quick-query ────────────────────────────────────────────────
if st.session_state.pending_query:
    pq = st.session_state.pending_query
    st.session_state.pending_query = None
    handle_query(pq)

# ── Chat input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about customers, tickets, or company policies…"):
    handle_query(prompt)
