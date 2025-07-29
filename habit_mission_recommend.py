import pandas as pd
import numpy as np
import oracledb
from datetime import datetime, timedelta
from pulp import LpProblem, LpVariable, lpSum, LpMaximize

# 데이터 선택 함수
def select_data(query):
    con = oracledb.connect(user="c##kurung", password="kurung2025",
                           dsn="localhost:1521/XE")
    cursor = con.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    con.close()
    return pd.DataFrame(rows, columns=columns)

# 습관 INSERT 함수
def insert_habits(habit_list):
    con = oracledb.connect(user="c##kurung", password="kurung2025", dsn="localhost:1521/XE")
    cursor = con.cursor()
    for rec in habit_list:
        cursor.execute(
            "INSERT INTO TB_MONTHLY_HABIT (USER_UUID, MONTHLY_HABIT_DATE, HABIT_REC_ID) VALUES (:1, :2, :3)",
            (rec["user_uuid"], rec["date"], rec["habit_rec_id"])
        )
    con.commit()
    con.close()

# 🧠 매월 습관 미션 생성 함수
def generate_monthly_habit_missions():
    # 1. 해당 월의 직전 달 Lifelog 데이터 불러오기
    today = datetime.now()
    last_month = today.replace(day=1) - timedelta(days=1)
    first_day = last_month.replace(day=1).strftime("%Y-%m-%d")
    last_day = last_month.strftime("%Y-%m-%d")
    insert_date = today.replace(day=1).date()   # 이번 달 1일 날짜(저장용)
    print(f"first_day: {first_day} ~ last_day: {last_day}" )

    # 전체 사용자 조회
    user_df = select_data("SELECT DISTINCT USER_UUID FROM TB_USER")
    habit_df = select_data("SELECT * FROM TB_HABIT_RECOMMENDED")

    if user_df.empty:
        print("사용자 데이터가 없습니다.")
        return

    # 사용자별 반복
    for _, user_row in user_df.iterrows():
        user_uuid = user_row["USER_UUID"]
        lifelog_df = select_data(f"""
            SELECT USER_UUID, LIFELOG_DATE, EMOTION, BED_TIME, WAKEUP_TIME, MEMO FROM TB_LIFELOG 
            WHERE USER_UUID = '{user_uuid}' AND LIFELOG_DATE BETWEEN TO_DATE('{first_day}', 'YYYY-MM-DD') AND TO_DATE('{last_day}', 'YYYY-MM-DD')""")

        if lifelog_df.empty:
            print(f"사용자 {user_uuid}의 라이프로그 데이터가 없습니다.")
            continue

        # 2. 감정 점수화
        emotion_score_map = {
            "행복함": 5, "신남": 4.5, "평온함": 4,
            "피곤함": 2.5, "불안함": 2, "우울함": 1.5,
            "슬픔": 1.5, "화남": 1
        }
        lifelog_df["emotion_score"] = lifelog_df["EMOTION"].map(emotion_score_map)

        # 3. 수면 시간 계산
        def calculate_sleep_hours(row):
            if pd.isnull(row["BED_TIME"]) or pd.isnull(row["WAKEUP_TIME"]):
                return np.nan
            sleep_time = row["BED_TIME"]
            wakeup_time = row["WAKEUP_TIME"]
            if wakeup_time < sleep_time:
                wakeup_time += pd.Timedelta(days=1)
            return (wakeup_time - sleep_time).total_seconds() / 3600

        lifelog_df["sleep_hours"] = lifelog_df.apply(calculate_sleep_hours, axis=1)

        # 4. 종합 점수 계산
        lifelog_df["total_score"] = (
                lifelog_df["emotion_score"].fillna(0) * 0.6 +
                lifelog_df["sleep_hours"].fillna(0) / 8 * 0.4
        )

        # 5. 최적화로 7개 습관 선택
        prob = LpProblem("HabitRecommendation", LpMaximize)
        habit_vars = [LpVariable(f"x_{i}", cat="Binary") for i in range(len(habit_df))]
        habit_scores = np.random.rand(len(habit_df))
        prob += lpSum([habit_scores[i] * habit_vars[i] for i in range(len(habit_df))])
        prob += lpSum(habit_vars) == 7
        prob.solve()

        selected_indices = [i for i, var in enumerate(habit_vars) if var.varValue == 1.0]
        selected_habits = habit_df.iloc[selected_indices]

        # 6. 결과 저장
        habit_list = []
        for i in range(7):
            habit = selected_habits.iloc[i]
            habit_list.append({
                "user_uuid": user_uuid,
                "date": insert_date,
                "habit_rec_id": int(habit["HABIT_REC_ID"])
            })

        insert_habits(habit_list)
        print("✔️ 습관 추천 7개가 DB에 저장되었습니다.")
