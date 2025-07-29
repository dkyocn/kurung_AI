# 📁 train_model.py
import pandas as pd
import xgboost as xgb
import joblib
from sklearn.preprocessing import OrdinalEncoder

# 파일 경로
medi_df = pd.read_csv("../mediData/medi_list.csv")
supp_df = pd.read_csv("../mediData/supp_list.csv")
inter_df = pd.read_csv("../mediData/interactions_train_id.csv")

# supp_id -> id 로 컬럼명 통일
supp_df = supp_df.rename(columns={
    "supp_id": "id",
    "supp_name": "name",
    "supp_name_ko": "name_ko"
})

# 통합 메타데이터
meta_df = pd.concat([medi_df, supp_df], ignore_index=True).set_index("id")

# Feature 생성
def make_feat(row):
    m1, m2 = meta_df.loc[row["id1"]], meta_df.loc[row["id2"]]
    return pd.Series({
        "category1": m1["category"],
        "category2": m2["category"],
        "company1": m1["company"],
        "company2": m2["company"],
        "is_supp1": int(m1.name >= 1000),
        "is_supp2": int(m2.name >= 1000)
    })

X = inter_df.apply(make_feat, axis=1, result_type="expand")
# y값을 숫자로 변형 -> 추후 활용 시 문자화 필요
level_map = {"Low": 0, "Moderate": 1, "High": 2}
y = inter_df["level"].map(level_map)

# 인코딩 및 모델 학습
enc = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
X_enc = enc.fit_transform(X)
model = xgb.XGBClassifier(eval_metric="mlogloss")
model.fit(X_enc, y)

# 저장
joblib.dump(model, "../mediPkl/xgb_model.pkl")
joblib.dump(enc, "../mediPkl/encoder.pkl")
print("✅ 모델 학습 및 저장 완료")
