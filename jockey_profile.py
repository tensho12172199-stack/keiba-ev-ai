import pandas as pd
import glob

df = pd.concat(
    [pd.read_csv(f) for f in glob.glob("data/*.csv")],
    ignore_index=True
)

df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
df = df.dropna(subset=["rank"])

df["pos_4c"] = (
    df["passing"].astype(str).str.split("-").str[-1].astype(float)
)

summary = (
    df.groupby("jockey")
    .agg(
        jockey_front_rate=("pos_4c", lambda x: (x <= 5).mean()),
        jockey_closer_rate=("pos_4c", lambda x: (x >= 10).mean()),
        jockey_avg_rank=("rank", "mean"),
        jockey_win_rate=("rank", lambda x: (x == 1).mean()),
    )
    .reset_index()
)

summary.to_csv("jockey_profile.csv", index=False)
