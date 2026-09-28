# NeoCarta + MySQL + Neo4j

Hướng dẫn ngắn gọn cài đặt và chạy NeoCarta v0.8.0 để lấy schema
metadata từ MySQL và ghi vào Neo4j.

## 1. Tạo môi trường Python và cài NeoCarta

``` powershel
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install "neocarta[cli,mcp]==0.8.0"
```

## 2. Cài Java

Cài Java 11 trở lên.

Ví dụ môi trường hiện tại:

``` text
Java 11.0.18
```

## 3. Cài SchemaCrawler

Tải SchemaCrawler 16.26.3:

``` powershell
Invoke-WebRequest `
  -Uri "https://github.com/schemacrawler/SchemaCrawler/releases/download/v16.26.3/schemacrawler-16.26.3-bin.zip" `
  -OutFile ".\schemacrawler-16.26.3-bin.zip"
```

Giải nén và đặt tại:

``` text
neocarta-mysql\schemacrawler-16.26.3-bin\
```

Cấu trúc chính:

``` text
schemacrawler-16.26.3-bin\
├── bin\
├── config\
└── lib\
```

SchemaCrawler cần FreeMarker trong classpath. Nếu bộ SchemaCrawler không
có FreeMarker phù hợp, thêm `freemarker-2.3.34.jar` vào thư mục `lib`.
(FreeMarker không đọc database và cũng không phân tích schema. Nó chỉ nhận kết quả mà SchemaCrawler đã thu thập rồi render theo template)

## 4. Cài MySQL Connector/J

Tải MySQL Connector/J và đặt file JAR tại:

``` text
neocarta-mysql\drivers\mysql-connector-j-<version>.jar
```

MySQL JDBC driver class:

``` text
com.mysql.cj.jdbc.Driver
```

## 5. Cấu hình bằng file `.env`

Tạo file:

``` text
neocarta-mysql\.env
```

Nội dung:

``` env
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=YOUR_NEO4J_PASSWORD
NEO4J_DATABASE=neo4j

# MySQL
JDBC_URL=jdbc:mysql://YOUR_MYSQL_HOST:YOUR_MYSQL_PORT/hisport
JDBC_USER=YOUR_MYSQL_USER
JDBC_PASSWORD=YOUR_MYSQL_PASSWORD
JDBC_DRIVER=com.mysql.cj.jdbc.Driver
JDBC_DRIVER_JAR=./drivers/mysql-connector-j-<version>.jar
SCHEMACRAWLER_JAR=./schemacrawler-16.26.3-bin/lib/*
```

NeoCarta tự đọc cấu hình từ `.env`, vì vậy không cần tạo các biến này trong Windows User Environment.

## 6. Chạy Neo4j

Neo4j cần chạy và expose Bolt tại:

``` text
bolt://localhost:7687
```

Nếu dùng Docker Compose:

``` powershell
docker compose up -d
```

## 7. Chạy NeoCarta

``` powershell
.\.venv\Scripts\Activate.ps1
```

Chạy ingest:

``` powershell
neocarta jdbc schema `
  --source-database-name "hisport" `
  --no-embeddings
```

Các thông tin kết nối JDBC, SchemaCrawler và Neo4j được NeoCarta đọc trực tiếp từ file `.env`.

Quy trình:

``` text
MySQL
  ↓
MySQL Connector/J
  ↓
SchemaCrawler + FreeMarker
  ↓
NeoCarta
  ↓
Neo4j
```

## 8. Sửa lỗi encoding trên Windows

Nếu chạy NeoCarta gặp:

``` text
UnicodeDecodeError: 'charmap' codec can't decode byte ...
```

mở:

``` text
neocarta-mysql\.venv\Lib\site-packages\
neocarta\connectors\jdbc\schema\extract.py
```

Trong `subprocess.run(...)`, thêm:

``` python
encoding="utf-8",
errors="replace",
```

Ví dụ:

``` python
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=self.timeout,
    env=env,
    check=False,
)
```

Sau đó chạy lại lệnh `neocarta jdbc schema`.

## 9. Kết quả

NeoCarta sẽ đọc metadata từ MySQL và tạo graph trong Neo4j, gồm các
thành phần như:

``` text
Database
  ↓
Schema
  ↓
Table
  ↓
Column
```

cùng các relationship metadata như foreign key/reference.
