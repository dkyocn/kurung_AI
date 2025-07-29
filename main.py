from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import oracledb
from starlette.middleware.cors import CORSMiddleware

import face_recognition
import cv2
import numpy as np
from PIL import Image
import io
import base64
import json
from datetime import datetime, timedelta
from jose import JWTError, jwt
# from passlib.context import CryptContext  # 임시로 주석 처리
from typing import Optional
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

# JWT 설정
SECRET_KEY = "vrDt6Hhffv9gPPEEHDBVhxY4W+gf//bxDgVljRr/+8z1ZxqEdgTmDDZ/UIquJuWQdZmJ8mz/DuzLF/pmcMFaqw=="
ALGORITHM = "HS512"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 비밀번호 해싱 (임시로 제거)
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 보안 설정
security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT 토큰 생성 함수
def create_token(data: dict, expires_delta: Optional[timedelta], category: str) -> str:
    """
    accessToken / refreshToken 모두 생성 가능
    :param data: 사용자 정보 (sub, userUuid, name, role 등)
    :param expires_delta: 토큰 만료 시간 (ex. 30분 or 24시간)
    :param category: "access" 또는 "refresh"
    :return: 인코딩된 JWT 문자열
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({
        "exp": expire,
        "category": category
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# JWT 토큰 검증 함수
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/db")
async def test_db():
    returnData = select_data("SELECT * FROM tb_diet")
    return returnData

# Face ID 등록 API
@app.post("/register-face")
async def register_face(
    user_id: str = Form(...),
    face_image: UploadFile = File(...)
):
    try:
        # 이미지 읽기
        image_data = await face_image.read()
        image = Image.open(io.BytesIO(image_data))
        image_array = np.array(image)

        # 얼굴 인코딩 추출
        face_encodings = face_recognition.face_encodings(image_array)

        if not face_encodings:
            raise HTTPException(status_code=400, detail="얼굴을 찾을 수 없습니다.")

        face_encoding = face_encodings[0]

        # 벡터 데이터 압축 (소수점 4자리로 제한)
        compressed_encoding = [round(float(x), 4) for x in face_encoding]
        face_encoding_str = json.dumps(compressed_encoding)

        # 데이터 크기 확인
        if len(face_encoding_str) > 900:  # 안전 마진
            # 더 강력한 압축 (소수점 3자리)
            compressed_encoding = [round(float(x), 3) for x in face_encoding]
            face_encoding_str = json.dumps(compressed_encoding)
            print(f"벡터 데이터 압축됨: {len(face_encoding_str)} 문자")

        # DB에 사용자 정보 저장
        try:
            con = oracledb.connect(user="c##kurung", password="kurung2025", dsn="localhost:1521/XE")
            cursor = con.cursor()

            # 기존 사용자 확인
            cursor.execute("""
                SELECT USER_ID, USER_FACELOGIN_YN FROM TB_USER WHERE USER_ID = :user_id
            """, {'user_id': user_id})

            user_exists = cursor.fetchone()

            if user_exists:
                # 기존 사용자 - Face ID 정보 업데이트
                cursor.execute("""
                    UPDATE TB_USER 
                    SET USER_FACELOGIN_YN = 1, 
                        USER_FACELOGIN_REF = :face_encoding
                    WHERE USER_ID = :user_id
                """, {
                    'user_id': user_id,
                    'face_encoding': face_encoding_str
                })
                print(f"기존 사용자 {user_id}의 Face ID 정보가 업데이트되었습니다.")

            con.commit()
            con.close()

            return {"message": "Face ID 등록이 완료되었습니다.", "user_id": user_id}

        except Exception as db_error:
            print(f"DB 오류: {str(db_error)}")
            raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(db_error)}")

    except Exception as e:
        print(f"Face ID 등록 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"등록 중 오류가 발생했습니다: {str(e)}")

# Face ID 로그인 API
@app.post("/login-face")
async def login_face(
    user_id: str = Form(...),
    face_image: UploadFile = File(...)
):
    try:
        # 1. 이미지에서 얼굴 인코딩 추출
        image_data = await face_image.read()
        image = Image.open(io.BytesIO(image_data))
        image_array = np.array(image)

        face_encodings = face_recognition.face_encodings(image_array)
        if not face_encodings:
            raise HTTPException(status_code=400, detail="얼굴을 찾을 수 없습니다.")
        current_face_encoding = face_encodings[0]

        # 2. DB에서 사용자 얼굴 벡터 가져오기
        with oracledb.connect(user="c##kurung", password="kurung2025", dsn="localhost:1521/XE") as con:
            cursor = con.cursor()
            cursor.execute("""
                SELECT USER_ID, USER_UUID, USER_NICK, USER_FACELOGIN_REF
                FROM TB_USER
                WHERE USER_FACELOGIN_YN = 1
                  AND USER_FACELOGIN_REF IS NOT NULL
                  AND USER_ID = :user_id
            """, {'user_id': user_id})


            user_row = cursor.fetchone()

        if not user_row:
            raise HTTPException(status_code=404, detail="등록된 Face ID 사용자가 아닙니다.")

        db_user_id, user_uuid, user_name, stored_face_encoding_json = user_row
        stored_face_encoding = np.array(json.loads(stored_face_encoding_json))

        # 3. 얼굴 유사도 비교
        face_distance = face_recognition.face_distance([stored_face_encoding], current_face_encoding)[0]
        if face_distance > 0.6:
            raise HTTPException(status_code=401, detail="등록되지 않은 얼굴입니다.")

        # 4. 토큰 생성
        access_token = create_token(
            data={
                "sub": db_user_id,
                "userUuid": user_uuid,
                "name": user_name,
                "role": "USER"
            },
            expires_delta=timedelta(minutes=30),
            category="access"
        )

        refresh_token = create_token(
            data={
                "sub": db_user_id,
                "userUuid": user_uuid,
                "name": user_name,
                "role": "USER"
            },
            expires_delta=timedelta(hours=24),
            category="refresh"
        )

        # 5. 응답
        return {
            "message": "Face ID 로그인 성공!",
            "username": db_user_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 중 오류가 발생했습니다: {str(e)}")

# 보호된 엔드포인트 (로그인 필요)
@app.get("/protected")
async def protected_route(current_user: str = Depends(verify_token)):
    return {"message": f"안녕하세요, {current_user}님!", "status": "authenticated"}

# 사용자 목록 조회 (관리자용)
@app.get("/users")
async def get_users():
    try:
        con = oracledb.connect(user="c##kurung", password="kurung2025", dsn="localhost:1521/XE")
        cursor = con.cursor()
        cursor.execute("SELECT id, username, created_at FROM users")
        users = cursor.fetchall()
        con.close()
        
        return {"users": [{"id": user[0], "username": user[1], "created_at": str(user[2])} for user in users]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"사용자 목록 조회 중 오류가 발생했습니다: {str(e)}")

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
