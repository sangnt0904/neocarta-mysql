# NeoCarta Text2SQL Agent for MySQL

Agent hỏi đáp dữ liệu MySQL bằng ngôn ngữ tự nhiên, dùng **NeoCarta
MCP + Neo4j Semantic Layer** để hiểu metadata và **FPT AI
`gpt-oss-120b`** để sinh SQL.

## 1. Kiến trúc

``` text
                    FPT gpt-oss-120b
                           ↕
                  Text2SQL Agent
                    run_agent.py
                  /              \
                 /                \
        NeoCarta MCP        execute_mysql_sql
             ↕                     ↕
           Neo4j              MySQL hisport
      Semantic Layer          dữ liệu thực
             ▲
             │
        NeoCarta JDBC
             ▲
             │
           MySQL
```

-   **MySQL `hisport`**: dữ liệu nghiệp vụ thực.
-   **NeoCarta JDBC**: đọc metadata MySQL và nạp vào Neo4j.
-   **Neo4j**: Semantic Layer/metadata graph.
-   **NeoCarta MCP**: cung cấp semantic metadata cho Agent.
-   **FPT AI `gpt-oss-120b`**: hiểu câu hỏi và sinh SQL.
-   **`execute_mysql_sql`**: chạy `SELECT` trên MySQL.

> NeoCarta MCP không chạy SQL trên MySQL. Agent dùng MCP để hiểu
> schema/semantic metadata, LLM viết SQL, sau đó MySQL tool thực thi
> SQL.

## 2. Cấu trúc project

``` text
F:\neocarta-mysql
├── run_agent.py
├── requirements.txt
├── agent\
│   ├── __init__.py
│   ├── agent.py
│   └── mysql_tool.py
├── drivers\
│   └── mysql-connector-j-26.7.0.jar
├── schemacrawler-16.26.3-bin\
│   └── lib\
└── .venv\
```

### `run_agent.py`

Entry point: khởi động NeoCarta MCP, lấy MCP tools, thêm
`execute_mysql_sql`, khởi tạo Agent, nhận câu hỏi và hiển thị
SQL/DATA/ANSWER.

### `agent/agent.py`

Cấu hình Agent và FPT LLM. Agent phải tra metadata trước, chỉ dùng
table/column đã xác nhận, dùng MySQL syntax, chỉ SELECT, không
`SELECT *`, giới hạn record và không bịa schema.

### `agent/mysql_tool.py`

Tool dùng SQLAlchemy + PyMySQL để thực thi SQL thật trên MySQL.

## 3. Yêu cầu

-   Windows + PowerShell
-   Python
-   Java 21
-   Docker Desktop
-   Neo4j Docker
-   SchemaCrawler
-   MySQL JDBC Driver
-   FPT AI API key

Neo4j:

``` text
Browser: http://localhost:7474/browser/
Bolt:    bolt://localhost:7687
```

## 4. Tạo virtual environment

``` powershell
cd F:\neocarta-mysql
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 5. Dependencies

`requirements.txt`:

``` text
neocarta[mcp]==0.8.0
fastmcp==2.14.7
langchain==1.4.0
langchain-litellm==0.7.1
langchain-mcp-adapters==0.3.2
SQLAlchemy==2.0.52
PyMySQL==1.2.0
```

Cài:

``` powershell
pip install -r requirements.txt
pip check
```

Kết quả mong đợi:

``` text
No broken requirements found.
```

## 6. Environment variables

Không hard-code password/API key trong source.

``` powershell
$env:JDBC_URL = "jdbc:mysql://<MYSQL_HOST>:<MYSQL_PORT>/hisport"
$env:JDBC_USER = "<MYSQL_USER>"
$env:JDBC_PASSWORD = "<MYSQL_PASSWORD>"
$env:JDBC_DRIVER = "com.mysql.cj.jdbc.Driver"
$env:JDBC_DRIVER_JAR = "./drivers/mysql-connector-j-26.7.0.jar"
$env:SCHEMACRAWLER_JAR = "./schemacrawler-16.26.3-bin/lib/*"

$env:NEO4J_URI = "bolt://localhost:7687"
$env:NEO4J_USERNAME = "neo4j"
$env:NEO4J_PASSWORD = "<NEO4J_PASSWORD>"
$env:NEO4J_DATABASE = "neo4j"

$env:FPT_API_KEY = "<FPT_API_KEY>"
$env:FPT_BASE_URL = "https://mkp-api.fptcloud.com/v1"
$env:AGENT_MODEL = "openai/gpt-oss-120b"

$env:MYSQL_URL = "mysql+pymysql://<MYSQL_USER>:<MYSQL_PASSWORD>@<MYSQL_HOST>:<MYSQL_PORT>/hisport"
```

Nếu password chứa ký tự đặc biệt trong URL thì cần URL-encode.

## 7. Nạp metadata MySQL vào Neo4j

``` powershell
neocarta jdbc schema `
  --jdbc-url "$env:JDBC_URL" `
  --jdbc-driver "$env:JDBC_DRIVER" `
  --jdbc-driver-jar "$env:JDBC_DRIVER_JAR" `
  --db-user "$env:JDBC_USER" `
  --source-database-name "hisport" `
  --no-embeddings
```

Không truyền wildcard SchemaCrawler trực tiếp qua `--schemacrawler-jar`
trên PowerShell. Giữ nó trong `$env:SCHEMACRAWLER_JAR`.

## 8. Semantic description

Khi phù hợp, đặt ý nghĩa cột bằng `COMMENT` trong MySQL rồi ingest JDBC
lại.

``` text
MySQL COLUMN COMMENT
        ↓
SchemaCrawler
        ↓
NeoCarta JDBC
        ↓
Neo4j Column.description
        ↓
NeoCarta MCP
        ↓
Text2SQL Agent
```

Kiểm tra:

``` cypher
MATCH (t:Table)-[:HAS_COLUMN]->(c:Column)
WHERE t.name = "booking"
  AND c.name IN ["bookingdate", "createtime"]
RETURN c.id, c.name, c.description;
```

Ví dụ ID hiện tại:

``` text
hisport..booking.bookingdate
hisport..booking.createtime
```

## 9. Chạy Agent

Đảm bảo Neo4j đang chạy và environment variables đã được cấu hình:

``` powershell
python .\run_agent.py
```

Ví dụ:

``` text
tìm những booking được đặt trong năm nay
```

Luồng:

``` text
Câu hỏi
   ↓
NeoCarta MCP → tìm semantic metadata
   ↓
LLM viết SQL
   ↓
execute_mysql_sql
   ↓
MySQL
   ↓
DATA
   ↓
ANSWER
```

Terminal nên hiển thị:

``` text
SQL:
SELECT ...

DATA:
...

ANSWER:
...
```

## 10. MySQL tool và an toàn

`execute_mysql_sql` chỉ cho phép `SELECT`. Danh sách record được giới
hạn, ví dụ:

``` python
MAX_ROWS = 30
```

Không cho Agent chủ động chạy `INSERT`, `UPDATE`, `DELETE`, `DROP`,
`ALTER`, `TRUNCATE`.

Trong production nên dùng thêm MySQL user chỉ có quyền `SELECT`; kiểm
tra SQL trong Python không nên là lớp bảo vệ duy nhất.

## 11. Quản lý context

Không dùng cố định một `thread_id` cho nhiều câu hỏi độc lập vì tool
output có thể tích lũy và vượt context.

``` python
import uuid
thread_id = str(uuid.uuid4())
```

``` python
config={
    "configurable": {
        "thread_id": thread_id
    }
}
```

## 12. Troubleshooting

### Thiếu `langchain_mcp_adapters`

``` powershell
pip install langchain-mcp-adapters==0.3.2
```

### `neocarta-mcp` đứng khi chạy trực tiếp

Bình thường: MCP server stdio đang chờ JSON-RPC từ MCP client. Nếu
`run_agent.py` tự khởi động MCP thì không cần chạy server bằng tay.

### Neo4j `Unauthorized`

Kiểm tra `$env:NEO4J_USERNAME` và `$env:NEO4J_PASSWORD` phải là
credential thật.

### Context length quá lớn

Tạo `thread_id` mới cho câu hỏi/phiên độc lập.

### SchemaCrawler wildcard lỗi trên PowerShell

Dùng:

``` powershell
$env:SCHEMACRAWLER_JAR = "./schemacrawler-16.26.3-bin/lib/*"
```

và không truyền wildcard trực tiếp qua CLI.

### Kiểm tra metadata

``` cypher
MATCH (d:Database)
RETURN d.name, d;
```

``` cypher
MATCH (t:Table)
RETURN t.name
ORDER BY t.name;
```

``` cypher
MATCH (t:Table)-[:HAS_COLUMN]->(c:Column)
RETURN t.name AS table, c.name AS column
ORDER BY table, column;
```

## 13. Nguyên tắc thiết kế

``` text
NeoCarta / Neo4j
= hiểu dữ liệu

LLM / Agent
= suy luận + viết SQL

MySQL Tool
= thực thi SQL trên dữ liệu thật
```

Semantic Layer không chứa toàn bộ business rows của MySQL. Nó cung cấp
context về schema, quan hệ và ý nghĩa nghiệp vụ để Agent tạo SQL chính
xác hơn.

## 14. Bảo mật

Không commit MySQL password, Neo4j password, FPT API key hoặc `.env`.

`.gitignore`:

``` gitignore
.venv/
.env
__pycache__/
*.pyc
```

Nếu credential từng bị lộ trong source/log/repository, nên rotate
credential.
