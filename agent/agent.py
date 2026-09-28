"""Text2SQL agent factory."""

import os

from langchain.agents import create_agent
from langchain.tools import BaseTool
from langchain_litellm import ChatLiteLLM
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph


SYSTEM_PROMPT = """
Workflow:
1. Search NeoCarta metadata only for the minimum tables and columns required.
2. Do not repeatedly fetch metadata for the same table.
3. Do not fetch metadata for unrelated tables.
4. Generate valid MySQL SQL.
5. Execute SQL using execute_mysql_sql.

Rules:
- Always inspect metadata before generating SQL.
- Only use tables and columns confirmed by metadata.
- Only execute read-only SELECT queries.
- Never use SELECT *.
- Select only the columns necessary to answer the question.
- For queries returning records, use LIMIT 30 unless the user explicitly asks for more.
- For counts or totals, use aggregate SQL instead of returning raw rows.
- Never invent tables or columns.

METADATA-ONLY QUESTIONS:

If the user asks about:
- what databases/schemas/tables/columns exist
- which tables are related to a business concept
- table relationships
- column meanings
- foreign keys
- available metadata

Use NeoCarta metadata tools only.

DO NOT call execute_mysql_sql for metadata-only questions.

Only call execute_mysql_sql when answering the question requires
actual business data stored in MySQL.
"""


DEFAULT_AGENT_MODEL = "openai/gpt-oss-120b"


def create_text2sql_agent(
    mcp_tools: list[BaseTool],
) -> CompiledStateGraph:

    model = ChatLiteLLM(
        model=os.getenv(
            "AGENT_MODEL",
            DEFAULT_AGENT_MODEL,
        ),
        api_key=os.getenv("FPT_API_KEY"),
        api_base=os.getenv(
            "FPT_BASE_URL",
            "https://mkp-api.fptcloud.com/v1",
        ),
        temperature=0,
    )

    return create_agent(
        model=model,
        tools=mcp_tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
    )