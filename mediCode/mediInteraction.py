import pandas as pd
import itertools
import joblib
import oracledb
import os

# ---------- 1. 데이터 로딩 ----------
# ⬇️ mediInteraction.py 파일이 있는 디렉토리 기준
base_dir = os.path.dirname(os.path.abspath(__file__))

medi_df = pd.read_csv(os.path.join(base_dir, '../mediData/medi_list.csv'))
meta_df = medi_df.set_index("id")
name_to_id = medi_df.set_index("name_ko")["id"].to_dict()
model = joblib.load(os.path.join(base_dir, '../mediPkl/xgb_model.pkl'))
enc = joblib.load(os.path.join(base_dir, '../mediPkl/encoder.pkl'))
inter_df = pd.read_csv(os.path.join(base_dir, '../mediData/interactions_train_id.csv'))

# ---------- 2. 설명 딕셔너리 ----------
desc_dict = {
    (min(r.id1, r.id2), max(r.id1, r.id2)): r.description
    for r in inter_df.itertuples(index=False)
}
inv_level = {0: "Low", 1: "Moderate", 2: "High"}
risk_kor = {"Low": "경미함", "Moderate": "중증도", "High": "심각함"}

# ---------- 3. AI 분석 + DB 저장 ----------
def analyze_interactions(user_uuid: str, user_input_names: list):
    print("🔍 입력된 약물명:", user_input_names)
    print("사용자 : ", user_uuid)
    try:
        user_ids = [int(name_to_id[n]) for n in user_input_names if n in name_to_id]
    except KeyError as e:
        raise ValueError(f"입력된 약물명 중 존재하지 않는 항목이 있습니다: {e}")

    pairs = list(itertools.combinations(user_ids, 2))
    print("🧪 분석할 쌍:", pairs)
    if not pairs:
        return []

    def make_feat(id1, id2):
        m1, m2 = meta_df.loc[id1], meta_df.loc[id2]
        return {
            "category1": m1["category"],
            "category2": m2["category"],
            "company1": m1["company"],
            "company2": m2["company"],
            "is_supp1": 0,
            "is_supp2": 0,
        }

    X = pd.DataFrame([make_feat(a, b) for a, b in pairs])
    X_enc = enc.transform(X)
    y_pred = model.predict(X_enc)

    # ---------- DB 연결 ----------
    con = oracledb.connect(user="c##kurung", password="kurung2025", dsn="localhost:1521/XE")
    cursor = con.cursor()

    # ---------- 결과 출력 ----------
    print("상호작용 예측 결과 (설명 있는 경우만 출력):")
    for (id1, id2), pred in zip(pairs, y_pred):
        name1 = meta_df.loc[id1]["name"]
        name2 = meta_df.loc[id2]["name"]
        desc = desc_dict.get((id1, id2)) or desc_dict.get((id2, id1))  # 순서 무관
        if desc:  # 설명이 존재할 때만 출력
            level = inv_level.get(pred, "Unknown")
            print(f"- {name1}, {name2}, {desc}, {level}")

    # ---------- 기존 결과 삭제 ----------
    cursor.execute("""
                   SELECT MEDI_INTER_ID
                   FROM TB_MEDICINE_INTERACTION
                   WHERE USER_UUID = :user_uuid
                   """, {'user_uuid': user_uuid})
    old_ids = cursor.fetchall()

    for (medi_inter_id,) in old_ids:
        # 🔁 먼저 TB_INPUT_MEDICINE에서 삭제
        cursor.execute("""
                       DELETE
                       FROM TB_INPUT_MEDICINE
                       WHERE MEDI_INTER_ID = :medi_inter_id
                       """, {'medi_inter_id': medi_inter_id})

        # 🔁 그 다음 TB_MEDICINE_INTERACTION 삭제
        cursor.execute("""
                       DELETE
                       FROM TB_MEDICINE_INTERACTION
                       WHERE MEDI_INTER_ID = :medi_inter_id
                       """, {'medi_inter_id': medi_inter_id})

    print("🔄 기존 데이터 삭제 완료")

# -------- 각 쌍별로 저장 ---------
    result_data = []

    for (id1, id2), pred in zip(pairs, y_pred):
        desc = desc_dict.get((id1, id2)) or desc_dict.get((id2, id1))
        if not desc:
            continue
        level = inv_level.get(pred, "Low")
        risk = risk_kor[level]

        # MEDI_INTERACTION 저장
        medi_inter_id_var = cursor.var(oracledb.NUMBER)
        cursor.execute("""
                       INSERT INTO TB_MEDICINE_INTERACTION (MEDI_INTER_ID, USER_UUID, INTERACTION)
                       VALUES (TB_MEDICINE_INTERACTION_SEQ.NEXTVAL, :1, :2) RETURNING MEDI_INTER_ID
                       INTO :3
                       """, (user_uuid, desc, medi_inter_id_var))
        medi_inter_id = int(medi_inter_id_var.getvalue()[0])

        # INPUT_MEDICINE 저장
        cursor.execute("""
                       INSERT INTO TB_INPUT_MEDICINE (INPUT_MEDI_ID, MEDI1_ID, MEDI2_ID, MEDI_INTER_ID, RISK)
                       VALUES (TB_INPUT_MEDICINE_SEQ.NEXTVAL, :1, :2, :3, :4)
                       """, (id1, id2, medi_inter_id, risk))

        name1_ko = meta_df.loc[id1]["name_ko"]
        name2_ko = meta_df.loc[id2]["name_ko"]
        result_data.append({
            "medicine1": {"nameKo": name1_ko},
            "medicine2": {"nameKo": name2_ko},
            "interResult": desc,
            "risk": risk
        })

    print("저장이 되었다능")

    con.commit()
    con.close()
    return result_data

if __name__ == "__main__":
    # 테스트용 입력값
    user_uuid = "2025061401"  # 예: 사용자 UUID
    user_input_names = ["몰핀", "엠파글리플로진"]  # 입력한 약물 이름 리스트

    try:
        result = analyze_interactions(user_uuid, user_input_names)
        print("✅ 분석 결과:")
        for r in result:
            print(f"- {r['medicine1']['nameKo']} + {r['medicine2']['nameKo']}: {r['interResult']} (위험도: {r['risk']})")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
