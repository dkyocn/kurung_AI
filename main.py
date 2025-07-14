from fastapi import FastAPI
import oracledb
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/db")
async def test_db():
    returnData = select_data("SELECT * FROM tb_diet")

    return returnData


def select_data(query):
    con = oracledb.connect(user="c##kurung", password="kurung2025",
                           dsn="localhost:1521/XE")  # DB에 연결 (호스트이름 대신 IP주소 가능)
    cursor = con.cursor()  # 연결된 DB 지시자(커서) 생성
    cursor.execute(query)
    outData = cursor.fetchall()

    con.close()
    return outData
