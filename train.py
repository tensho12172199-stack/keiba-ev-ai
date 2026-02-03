# train.py
import glob
import os
import pandas as pd
import lightgbm as lgb
from preprocess_advanced import preprocess_advanced

DATA_DIR = r"C:\Users\tensh\OneDrive\デスクトップ\競馬予想\data"

csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
assert len(csv_files) > 0, "CSVが見つかりません"

X_list = []
y_list = []

for f in csv_files:
    print(f"processing: {os.path.basename(f)}")
    df = pd.read_csv(f)

    X, y, feats = preprocess_advanced(df)

    X_list.append(X)
    y_list.append(y)

X_all = pd.concat(X_list, ignore_index=True)
y_all = pd.concat(y_list, ignore_index=True)

print("================================")
print("train data:", X_all.shape)
print("win rate:", y_all.mean())
print("================================")

train_data = lgb.Dataset(X_all, label=y_all)

params = {
    "objective": "binary",
    "metric": "binary_logloss",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "max_depth": -1,
    "verbose": -1,
}

model = lgb.train(
    params,
    train_data,
    num_boost_round=400
)

model.save_model("horse_racing_full_model.txt")
print("model saved!")
