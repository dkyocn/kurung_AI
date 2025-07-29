# 📁 recommend_supp.py
import pandas as pd
import joblib
import random

# 1) 데이터 로딩 및 메타 구성
medi_df = pd.read_csv("../mediData/medi_list.csv")
supp_df = pd.read_csv("../mediData/supp_list.csv").rename(columns={
    "supp_id": "id",
    "supp_name": "name",
    "supp_name_ko": "name_ko"
})
meta_df = pd.concat([medi_df, supp_df], ignore_index=True).set_index("id")

# 이름→ID 맵
name_to_id = meta_df.reset_index().set_index("name")["id"].to_dict()

# 2) 모델·인코더 로딩
model = joblib.load("../mediPkl/xgb_model.pkl")
enc   = joblib.load("../mediPkl/encoder.pkl")

# 3) 사용자 입력 (이름 리스트 → ID 리스트)
user_input_names = [
    "L-Carnitine", "Levofloxacin", "Warfarin",
    "Glucosamine", "Chondroitin", "Vitamin K1"
]
taken_ids = [int(name_to_id[n]) for n in user_input_names]

# 복용군 카테고리 집합 (다양성 보너스용)
user_categories = {meta_df.loc[tid]["category"] for tid in taken_ids}

# 4) 추천 후보 풀 (영양제 ID만)
supp_ids = supp_df["id"].tolist()

# 5) 피처 생성 함수
def make_feat(id1, id2):
    m1, m2 = meta_df.loc[id1], meta_df.loc[id2]
    return {
        "category1": m1["category"],
        "category2": m2["category"],
        "company1":  m1["company"],
        "company2":  m2["company"],
        "is_supp1":  int(id1 >= 1000),
        "is_supp2":  int(id2 >= 1000),
    }

# 6) “Low” 클래스 인덱스 자동 탐지
classes = list(model.classes_)
if any(isinstance(c, str) for c in classes):
    # 문자열 클래스 중 소문자 비교
    low_label = next((c for c in classes if str(c).lower() == "low"), None)
    if low_label is None:
        raise ValueError(f"'Low' 클래스가 model.classes_에 없습니다: {classes}")
    low_idx = classes.index(low_label)
else:
    # numeric classes [0,1,2] 인 경우 0이 Low
    low_idx = classes.index(0)

# 7) 후보별 안전도+다양성 스코어링
scores = []
for sid in supp_ids:
    if sid in taken_ids:
        continue

    # 1) 모든 복용군과 조합→ P(Low) 확률
    feats = [make_feat(sid, tid) for tid in taken_ids]
    X = enc.transform(pd.DataFrame(feats))
    probs = model.predict_proba(X)
    p_lows = probs[:, low_idx]
    safety_score = float(p_lows.min())  # 최저 확률(가장 위험한 조합 기준)

    # 2) 다양성 보너스
    bonus = 0.1 if meta_df.loc[sid]["category"] not in user_categories else 0.0

    scores.append((sid, safety_score + bonus))

# 내림차순 정렬 → 상위 3개
top3 = [sid for sid, _ in sorted(scores, key=lambda x: x[1], reverse=True)[:3]]

# 8) 결과 출력
print("✅ 추천 영양제 Top 3 (안전도+다양성 기준):")
for sid in top3:
    r = meta_df.loc[sid]
    print(f"- {r['name']} ({r['name_ko']}) — {r['category']} / ")
