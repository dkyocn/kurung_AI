from fastapi import FastAPI
import oracledb
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

# 매일 운동 미션
# ⬇️ 운동 미션 생성 함수 가져오기
from exercise_recommend_mission import generate_daily_exercise_missions
# 습관 미션 생성 함수 가져오기
from habit_mission_recommend import generate_monthly_habit_missions

# ✅ 스케줄러에 등록할 함수
def schedule_exercise_mission():
    print(f"[{datetime.now()}] 운동 미션 생성 시작")
    generate_daily_exercise_missions()
    print(f"[{datetime.now()}] 운동 미션 생성 완료")

def schedule_habit_mission():
    print(f"[{datetime.now()}] 습관 미션 생성 시작")
    generate_monthly_habit_missions()
    print(f"[{datetime.now()}] 습관 미션 생성 완료")

# ✅ FastAPI lifespan 내에 스케줄러 포함
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    # scheduler.add_job(schedule_exercise_mission, 'cron', hour=0, minute=0)  # 매일 00시 00분 실행
    # scheduler.add_job(schedule_habit_mission, 'cron', day=1, hour=0, minute=0)
    # ✅ 테스트용 (30초마다 실행)
    # scheduler.add_job(schedule_exercise_mission, 'interval', seconds=10)
    scheduler.add_job(schedule_habit_mission, 'interval', seconds=10)
    scheduler.start()
    yield
    scheduler.shutdown()

# ✅ FastAPI 앱 정의 (lifespan 포함)
app = FastAPI(lifespan=lifespan)

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

@app.get("/habit")
async def test_habit():
    returnHabitData = select_data("SELECT * FROM TB_HABIT_RECOMMENDED")

    return returnHabitData


def select_data(query):
    con = oracledb.connect(user="c##kurung", password="kurung2025",
                           dsn="localhost:1521/XE")  # DB에 연결 (호스트이름 대신 IP주소 가능)
    cursor = con.cursor()  # 연결된 DB 지시자(커서) 생성
    cursor.execute(query)
    outData = cursor.fetchall()
    con.close()
    return outData
