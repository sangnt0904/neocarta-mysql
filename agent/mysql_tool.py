import os

from langchain.tools import tool
from sqlalchemy import create_engine, text


MYSQL_URL = os.getenv(
    "MYSQL_URL"    
)

engine = create_engine(
    MYSQL_URL,
    pool_pre_ping=True,
)

def truncate_value(value, max_length=500):
    if isinstance(value, str) and len(value) > max_length:
        return value[:max_length] + "..."

    return value

@tool
def execute_mysql_sql(sql: str) -> str:
    """
    Execute a read-only SQL query against the MySQL hisport database.

    Only SELECT statements are allowed.
    """

    cleaned = sql.strip().lower()

    if not cleaned.startswith("select"):
        return "ERROR: Only SELECT statements are allowed."

    try:
        MAX_ROWS = 30

        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = result.fetchmany(MAX_ROWS)

        data = {
            "columns": columns,
            "rows": [
                [
                    truncate_value(value)
                    for value in row
                ]
                for row in rows
            ],
            "row_limit": MAX_ROWS,
        }

        return str(data)

    except Exception as e:
        return f"ERROR: {e}"