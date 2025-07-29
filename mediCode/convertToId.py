# convert_interactions_to_id.py
import pandas as pd
import os

BASE   = "D:/python_workspace/MediTest"   # 프로젝트 루트 경로
MEDI   = os.path.join(BASE, "mediData", "medi_list.csv")
SUPP   = os.path.join(BASE, "mediData", "supp_list.csv")
INTER  = os.path.join(BASE, "mediData", "interactions_train.csv")     # name 기반
OUT    = os.path.join(BASE, "mediData", "interactions_train_id.csv")  # id 기반 결과

# 1) 약물 + 영양제 메타 로드 ▶ name → id 매핑
medi_df = pd.read_csv(MEDI).rename(columns={"medi_id": "id", "medi_name": "name"})
# supp_df = pd.read_csv(SUPP).rename(columns={"supp_id": "id", "supp_name": "name"})
meta_df = pd.concat([medi_df, medi_df], ignore_index=True)

name_to_id = meta_df.set_index("name")["id"].to_dict()

# 2) 상호작용 파일 로드
inter_df = pd.read_csv(INTER)

# 3) 이름 → id 변환
def map_name(n):
    if n not in name_to_id:
        print(f"❗ 매핑 실패: {n}")
        return None
    return name_to_id[n]

inter_df["id1"] = inter_df["id1"].apply(map_name)
inter_df["id2"] = inter_df["id2"].apply(map_name)

# 4) 매핑 실패한 행 제거
before = len(inter_df)
inter_df = inter_df.dropna(subset=["id1", "id2"]).astype({"id1": "int64", "id2": "int64"})
after = len(inter_df)
print(f"✅ 변환 완료: {before}->{after}행 유지")

# 5) 저장
inter_df.to_csv(OUT, index=False)
print(f"📄 저장: {OUT}")
