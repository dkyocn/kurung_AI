import pandas as pd
import oracledb
from datetime import datetime

def generate_daily_exercise_missions():
    def select_data(query):
        con = oracledb.connect(user="c##kurung", password="kurung2025", dsn="localhost:1521/XE")
        cursor = con.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        df = pd.DataFrame(rows, columns=columns)
        con.close()
        return df

    def insert_daily_mission(user_uuid, exercise_rec_id, today):
        con = oracledb.connect(user="c##kurung", password="kurung2025", dsn="localhost:1521/XE")
        cursor = con.cursor()
        cursor.execute("""
            INSERT INTO TB_MISSIONS (
                MISSION_ID, USER_UUID, STARTED_DATE,
                IS_COMPLETED, DISPLAY_TYPE, TOGGLE_OPTION, EXERCISE_REC_ID
            ) VALUES (
                TB_MISSIONS_SEQ.NEXTVAL, :1, TO_DATE(:2, 'YYYY-MM-DD'),
                0, 'EXERCISE', 1, :3
            )
        """, (user_uuid, today, exercise_rec_id))
        con.commit()
        con.close()

    # 오늘 날짜
    today = datetime.today().strftime("%Y-%m-%d")

    # 사용자 UUID 전체 조회
    user_df = select_data("SELECT DISTINCT USER_UUID FROM TB_USER")

    # 추천 운동 풀 조회
    exercise_pool = select_data("SELECT * FROM TB_EXERCISE_RECOMMENDED")
    print("추천 운동 컬럼:", exercise_pool.columns.tolist())

    # 사용자별 1개 추천
    for user_uuid in user_df["USER_UUID"]:
        check = select_data(f"""
            SELECT COUNT(*) AS CNT FROM TB_MISSIONS
            WHERE USER_UUID = '{user_uuid}' AND STARTED_DATE = TO_DATE('{today}', 'YYYY-MM-DD')
            AND DISPLAY_TYPE = 'EXERCISE'
        """)
        if check["CNT"].iloc[0] > 0:
            print(f"⏩ {user_uuid}: 이미 운동 미션 있음")
            continue

        selected = exercise_pool.sample(n=1).iloc[0]
        exercise_rec_id = int(selected["EXERCISE_REC_ID"])
        insert_daily_mission(user_uuid, exercise_rec_id, today)
        print(f"✅ {user_uuid}: 운동 미션 추천 완료")
