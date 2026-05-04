import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

db_url = f"mysql+pymysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}:{os.getenv('MYSQL_PORT')}/{os.getenv('MYSQL_DATABASE')}"
engine = create_engine(db_url)

with engine.connect() as conn:
    tables = conn.execute(text("SHOW TABLES")).fetchall()
    print("Tabelas encontradas no banco de dados:")
    for t in tables:
        print(f"- {t[0]}")