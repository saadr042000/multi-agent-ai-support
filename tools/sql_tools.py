"""
SQL Agent Tools
Converts natural language queries to SQLite SQL and executes them.
"""
import sqlite3
import json
import anthropic
from config import DB_PATH, MODEL, ANTHROPIC_API_KEY


def _get_client():
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def get_db_schema() -> str:
    """Return a human-readable schema of the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    schema_parts = []
    for (table_name,) in tables:
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = cursor.fetchall()
        col_defs = [f"  {c[1]} {c[2]}" for c in cols]
        schema_parts.append(f"Table: {table_name}\n" + "\n".join(col_defs))

    # Sample rows to help LLM understand values
    for (table_name,) in tables:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 2")
        rows = cursor.fetchall()
        if rows:
            schema_parts.append(f"Sample rows from {table_name}: {rows}")

    conn.close()
    return "\n\n".join(schema_parts)


def run_sql(query: str) -> str:
    """Execute a raw SQL SELECT query and return JSON results."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "[]  (no results found)"
        return json.dumps([dict(r) for r in rows], indent=2, default=str)
    except Exception as e:
        return f"SQL Error: {e}"


def nl_to_sql_and_run(natural_query: str) -> dict:
    """
    Main entry-point for the SQL agent.
    Returns {"sql": ..., "raw_results": ..., "summary": ...}
    """
    schema = get_db_schema()
    client = _get_client()

    # Step 1 – generate SQL
    sql_response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=f"""You are a SQLite expert. Convert the user's natural-language question into a 
single valid SQLite SELECT statement using the schema below. 
Return ONLY the SQL — no markdown fences, no explanations.

Schema:
{schema}

Rules:
- Read-only SELECT only.
- Use LIKE with wildcards for name/text searches (e.g. WHERE name LIKE '%Ema%').
- LIMIT 50 unless user asks for everything.
- Join tables when needed.
""",
        messages=[{"role": "user", "content": natural_query}],
    )

    sql_query = sql_response.content[0].text.strip().strip("```sql").strip("```").strip()
    raw_results = run_sql(sql_query)

    return {
        "sql": sql_query,
        "raw_results": raw_results,
    }
