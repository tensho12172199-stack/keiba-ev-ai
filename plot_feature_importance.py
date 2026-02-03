import lightgbm as lgb
import pandas as pd
import matplotlib.pyplot as plt

MODEL_PATH = "horse_racing_full_model.txt"

# ===== モデル読み込み =====
model = lgb.Booster(model_file=MODEL_PATH)

# ===== 重要度（gain）=====
importance = model.feature_importance(importance_type="gain")
features = model.feature_name()

df_imp = (
    pd.DataFrame({
        "feature": features,
        "importance": importance
    })
    .sort_values("importance", ascending=False)
)

print(df_imp.head(20))

# ===== プロット =====
plt.figure(figsize=(8, 10))
plt.barh(df_imp["feature"][:20], df_imp["importance"][:20])
plt.gca().invert_yaxis()
plt.title("LightGBM Ranker Feature Importance (gain)")
plt.tight_layout()
plt.show()
