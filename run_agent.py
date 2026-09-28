"""Entry point for running the Text2SQL agent with MCP server."""

import asyncio
import os
import uuid
import httpx
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

from agent.agent import create_text2sql_agent
from agent.mysql_tool import execute_mysql_sql
import sys
from pathlib import Path


load_dotenv()

# Env vars forwarded to the MCP subprocess. `StdioServerParameters` rejects
# None values, so any var not set in the parent environment is dropped below.
# Provider auth vars (OPENAI_API_KEY, GEMINI_API_KEY, COHERE_API_KEY, ...) are
# passed through if present so LiteLLM in the MCP server can pick them up.
_mcp_env_candidates = {
    "NEO4J_URI": os.getenv("NEO4J_URI"),
    "NEO4J_USERNAME": os.getenv("NEO4J_USERNAME"),
    "NEO4J_PASSWORD": os.getenv("NEO4J_PASSWORD"),
    "NEO4J_DATABASE": os.getenv("NEO4J_DATABASE"),
    "EMBEDDING_MODEL": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
    # Provider credentials — set the ones your EMBEDDING_MODEL needs.
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    # "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),  # noqa: ERA001
    # "COHERE_API_KEY": os.getenv("COHERE_API_KEY"),  # noqa: ERA001
    # "AZURE_API_KEY": os.getenv("AZURE_API_KEY"),  # noqa: ERA001
    # "AZURE_API_BASE": os.getenv("AZURE_API_BASE"),  # noqa: ERA001
    # "AZURE_API_VERSION": os.getenv("AZURE_API_VERSION"),  # noqa: ERA001
    # "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),  # noqa: ERA001
    # "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),  # noqa: ERA001
    # "AWS_REGION_NAME": os.getenv("AWS_REGION_NAME"),  # noqa: ERA001
}
mcp_name = "neocarta-mcp.exe" if os.name == "nt" else "neocarta-mcp"
mcp_exe = Path(sys.executable).parent / mcp_name

print("MCP executable:", mcp_exe)
print("Exists:", mcp_exe.exists())

sql_metadata_graph_mcp_params = {
    "transport": "stdio",
    "command": str(mcp_exe),
    "args": [],
    "env": {
        k: v
        for k, v in _mcp_env_candidates.items()
        if v is not None
    },
}
client = MultiServerMCPClient(
    {
        "sql_metadata_graph": sql_metadata_graph_mcp_params,
    }
)

CONFIG = {"configurable": {"thread_id": "1"}}


# run the agent with MCP server using stdio transport
async def main():
    client = MultiServerMCPClient(
        {
            "sql_metadata_graph": sql_metadata_graph_mcp_params,
        }
    )

    neocarta_tools = await client.get_tools(
        server_name="sql_metadata_graph"
    )

    NEEDED_TOOLS = {
        "list_schemas",
        "list_tables_by_schema",
        "get_context_by_table_full_text_search",
        "get_context_by_column_full_text_search",
    }

    filtered_neocarta_tools = [
        tool
        for tool in neocarta_tools
        if tool.name in NEEDED_TOOLS
    ]

    print("NeoCarta tools enabled:")
    for tool in filtered_neocarta_tools:
        print(" -", tool.name)

    allowed_tools = filtered_neocarta_tools + [
        execute_mysql_sql
    ]

    agent = create_text2sql_agent(allowed_tools)

    print("\n===================================== Chat =====================================\n")

    while True:
        user_input = input("> ").strip()

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit"]:
            break

        # Mỗi câu hỏi sử dụng context mới
        thread_id = str(uuid.uuid4())

        async for chunk in agent.astream(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_input,
                    }
                ]
            },
            config={
                "configurable": {
                    "thread_id": thread_id
                }
            },
        ):
            for _, update in chunk.items():

                if "messages" not in update:
                    continue

                latest_message = update["messages"][-1]

                # =========================
                # 1. In SQL khi agent gọi MySQL
                # =========================
                tool_calls = getattr(latest_message, "tool_calls", None)

                if tool_calls:
                    for tool_call in tool_calls:
                        if tool_call.get("name") == "execute_mysql_sql":
                            sql = tool_call.get("args", {}).get("sql")

                            if sql:
                                print("\nSQL:")
                                print(sql)

                    continue

                # =========================
                # 2. In dữ liệu MySQL raw
                # =========================
                if latest_message.__class__.__name__ == "ToolMessage":

                    tool_name = getattr(latest_message, "name", None)

                    if tool_name == "execute_mysql_sql":
                        print("\nDATA:")
                        print(latest_message.content)

                    continue

                # =========================
                # 3. In final answer của AI
                # =========================
                if latest_message.__class__.__name__ != "AIMessage":
                    continue

                content = latest_message.content

                if not content:
                    continue

                if isinstance(content, list):
                    final_texts = []

                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            final_texts.append(item.get("text", ""))

                    if final_texts:
                        print("\nANSWER:")
                        print("\n".join(final_texts))

                elif isinstance(content, str):
                    print("\nANSWER:")
                    print(content)


if __name__ == "__main__":
    asyncio.run(main())