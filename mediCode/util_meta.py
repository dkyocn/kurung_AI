import os, pandas as pd

BASE = os.path.dirname(__file__)
MEDI_CSV = os.path.join(BASE, "mediData", "medi_list.csv")
SUPP_CSV = os.path.join(BASE, "mediData", "supp_list.csv")

def load_meta() -> pd.DataFrame:
    """약물(ID 1~) + 영양제(ID 1001~) 통합 DataFrame 반환, id 인덱스"""
    drug_df = pd.read_csv(MEDI_CSV)
    supp_df = pd.read_csv(SUPP_CSV)

    drug_df["is_supp"] = 0
    supp_df["is_supp"] = 1

    meta = pd.concat([drug_df, supp_df], ignore_index=True)

    # id 기준 고유성 확보
    meta = meta.drop_duplicates(subset="id", keep="first")

    return meta.set_index("id")            # ★ id 인덱스
