import pandas as pd
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, root_mean_squared_error
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
import joblib                        # to save trained models
import os
import numpy as np
from sklearn.model_selection import GroupKFold
import matplotlib.pyplot as plt

csv_dir = "csvs"
csvs = os.listdir(csv_dir)

dataframes = []
cnt = 0
for csv in csvs:
    file_path = os.path.join(csv_dir,csv)
    if csv.endswith(".csv"):
        df = pd.read_csv(file_path)
        df['flow_id']=cnt
        cnt+=1
        # df['flow_id']="".join([ele for ele in csv if ele.isdigit()])
        dataframes.append(df)
merged_dataframe = pd.concat(dataframes, ignore_index=True)
data = merged_dataframe.copy()
fullcolumns = data.columns.tolist()
data = data[data["skb.data_len"]>400]
# data.to_csv('data.csv', index=False)


# -------------------------------------------------
# 2.  Feature / target / groups  -------------------
DROP_COLS   = ["Time", "Sequence", "tp_rtt_seq", "tp_rcv_tstamp","skb.data_len"]
FS_COLUMNS  = ["FlightSizeRef", "FlightSizeLin"]              # later dropped
TARGET_COL  = "FlightSizeRef"
GROUP_COL   = "flow_id"        

X_full = data.drop(columns=DROP_COLS)
y_full = data[TARGET_COL].values
groups = data[GROUP_COL].values


# -------------------------------
# 3.  Two‑Way Split: 80% Train, 20% Test
#     (Ensure no overlap of flow_ids)
# -------------------------------
gss = GroupShuffleSplit(test_size=0.20, n_splits=1, random_state=42)
train_idx, test_idx = next(gss.split(X_full, y_full, groups=groups))
X_train_wFS = X_full.iloc[train_idx]
X_test_wFS  = X_full.iloc[test_idx]
y_train     = y_full[train_idx]
y_test      = y_full[test_idx]
groups_train = groups[train_idx]
groups_test  = groups[test_idx]

# -------------------------------
# 4.  Drop Flight‑Size & Group Columns
#     so that models cannot “peek”
# -------------------------------
X_train = X_train_wFS.drop(columns=FS_COLUMNS + [GROUP_COL])
X_test  = X_test_wFS.drop(columns=FS_COLUMNS + [GROUP_COL])
feature_names = X_train.columns.tolist()
print(feature_names)
print(len(feature_names))

# Linux baseline
Linux_fs  = X_test_wFS['FlightSizeLin']
print("Linux ➜  RMSE %.1f   R² %.3f"
      % (root_mean_squared_error(y_test, Linux_fs),
         r2_score(y_test, Linux_fs)))

# ------------------------------------------------------------------
# XGBoost  -----------------------------------------------------
xgb = XGBRegressor(
        n_estimators=866, max_depth=8, learning_rate=0.07,
        subsample=0.92, colsample_bytree=0.63,
        objective="reg:squarederror", tree_method="hist",
        eval_metric="rmse", n_jobs=-1, random_state=42)
xgb.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

xgb.save_model("xgb_model.json")
xgb.save_model("xgb_model.bin")
