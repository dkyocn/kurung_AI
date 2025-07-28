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

app = FastAPI()

# JWT 설정
SECRET_KEY = "your-secret-key-here"  # 실제 운영환경에서는 환경변수로 관리
ALGORITHM = "HS256"
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
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

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
    username: str = Form(...),
    password: str = Form(...),
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
            """, {'user_id': username})
            
            user_exists = cursor.fetchone()
            
            if user_exists:
                # 기존 사용자 - Face ID 정보 업데이트
                cursor.execute("""
                    UPDATE TB_USER 
                    SET USER_FACELOGIN_YN = 1, 
                        USER_FACELOGIN_REF = :face_encoding,
                        USER_PWD = :password
                    WHERE USER_ID = :user_id
                """, {
                    'user_id': username,
                    'password': password,
                    'face_encoding': face_encoding_str
                })
                print(f"기존 사용자 {username}의 Face ID 정보가 업데이트되었습니다.")
            else:
                # 새 사용자 등록 - TB_USER 테이블 구조에 맞춤
                cursor.execute("""
                    INSERT INTO TB_USER (
                        USER_UUID, USER_ID, USER_FACELOGIN_YN, USER_FACELOGIN_REF, 
                        USER_PWD, USER_NICK, USER_GENDER, USER_AGE, 
                        USER_KEY, USER_PATH, PROFILE_IMG, IS_ACTIVE, ADMIN_YN, USER_REFRESH_TOKEN
                    ) VALUES (
                        :user_uuid, :user_id, 1, :face_encoding,
                        :password, :nickname, 'MALE', TO_DATE('1990-01-01', 'YYYY-MM-DD'),
                        NULL, 'NORMAL', NULL, 1, 0, NULL
                    )
                """, {
                    'user_uuid': f"FACE_{int(datetime.now().timestamp())}",
                    'user_id': username,
                    'password': password,
                    'face_encoding': face_encoding_str,
                    'nickname': username
                })
                print(f"새 사용자 {username}이 등록되었습니다.")
            
            con.commit()
            con.close()
            
            return {"message": "Face ID 등록이 완료되었습니다.", "username": username}
            
        except Exception as db_error:
            print(f"DB 오류: {str(db_error)}")
            raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(db_error)}")
        
    except Exception as e:
        print(f"Face ID 등록 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=f"등록 중 오류가 발생했습니다: {str(e)}")

# Face ID 로그인 API
@app.post("/login-face")
async def login_face(face_image: UploadFile = File(...)):
    try:
        # 이미지 읽기
        image_data = await face_image.read()
        image = Image.open(io.BytesIO(image_data))
        image_array = np.array(image)
        
        # 얼굴 인코딩 추출
        face_encodings = face_recognition.face_encodings(image_array)
        
        if not face_encodings:
            raise HTTPException(status_code=400, detail="얼굴을 찾을 수 없습니다.")
        
        current_face_encoding = face_encodings[0]
        
        # DB에서 Face ID가 활성화된 사용자들의 얼굴 인코딩 가져오기
        try:
            con = oracledb.connect(user="c##kurung", password="kurung2025", dsn="localhost:1521/XE")
            cursor = con.cursor()
            
            cursor.execute("""
                SELECT USER_ID, USER_FACELOGIN_REF 
                FROM TB_USER 
                WHERE USER_FACELOGIN_YN = 1 AND USER_FACELOGIN_REF IS NOT NULL
            """)
            users = cursor.fetchall()
            con.close()
            
            # 얼굴 인식 비교
            for user in users:
                user_id, stored_face_encoding_json = user
                
                if stored_face_encoding_json:
                    stored_face_encoding = np.array(json.loads(stored_face_encoding_json))
                    
                    # 얼굴 유사도 계산
                    face_distance = face_recognition.face_distance([stored_face_encoding], current_face_encoding)[0]
                    
                    # 임계값 0.6 이하일 때 인식 성공
                    if face_distance <= 0.6:
                        # JWT 토큰 생성
                        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                        access_token = create_access_token(
                            data={"sub": user_id}, expires_delta=access_token_expires
                        )
                        
                        return {
                            "message": "Face ID 로그인 성공!",
                            "username": user_id,
                            "access_token": access_token,
                            "token_type": "bearer"
                        }
            
            raise HTTPException(status_code=401, detail="등록되지 않은 얼굴입니다.")
            
        except Exception as db_error:
            print(f"DB 오류: {str(db_error)}")
            raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(db_error)}")
        
    except Exception as e:
        print(f"Face ID 로그인 오류: {str(e)}")
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

def select_data(query):
    con = oracledb.connect(user="c##kurung", password="kurung2025",
                           dsn="localhost:1521/XE")  # DB에 연결 (호스트이름 대신 IP주소 가능)
    cursor = con.cursor()  # 연결된 DB 지시자(커서) 생성
    cursor.execute(query)
    outData = cursor.fetchall()

    con.close()
    return outData
