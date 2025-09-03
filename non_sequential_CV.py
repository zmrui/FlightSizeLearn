#!/usr/bin/env python
# coding: utf-8

# In[1]:


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
import matplotlib


# In[2]:


csv_dir = "csvs"
csvs = os.listdir(csv_dir)


# In[3]:


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


# In[4]:


data


# In[5]:


# -------------------------------------------------
# 2.  Feature / target / groups  -------------------
DROP_COLS   = ["Time", "Sequence", "tp_rtt_seq", "tp_rcv_tstamp"]
FS_COLUMNS  = ["FlightSizeRef", "FlightSizeLin"]              # later dropped
TARGET_COL  = "FlightSizeRef"
GROUP_COL   = "flow_id"        # <-- ***adjust to your real column name***


# In[6]:


# *X* still contains FS columns for a moment; we’ll drop them *after* splitting
X_full = data.drop(columns=DROP_COLS)
y_full = data[TARGET_COL].values
groups = data[GROUP_COL].values


# In[7]:


# -------------------------------
# 3.  Two‑Way Split: 80% Train, 20% Test
#     (Ensure no overlap of flow_ids)
# -------------------------------
gss = GroupShuffleSplit(test_size=0.20, n_splits=1, random_state=123)
train_idx, test_idx = next(gss.split(X_full, y_full, groups=groups))


# In[8]:


X_train_wFS = X_full.iloc[train_idx]
X_test_wFS  = X_full.iloc[test_idx]
y_train     = y_full[train_idx]
y_test      = y_full[test_idx]
groups_train = groups[train_idx]
groups_test  = groups[test_idx]


# In[9]:


print(f"Training rows: {len(train_idx)},  Test rows: {len(test_idx)}")
print(f"Unique flows in train: {np.unique(groups_train).shape[0]},  Unique flows in test: {np.unique(groups_test).shape[0]}")
print("Overlap between train/test flows:", len(set(groups_train) & set(groups_test)))  # should be 0


# In[10]:


# -------------------------------
# 4.  Drop Flight‑Size & Group Columns
#     so that models cannot “peek”
# -------------------------------
X_train = X_train_wFS.drop(columns=FS_COLUMNS + [GROUP_COL])
X_test  = X_test_wFS.drop(columns=FS_COLUMNS + [GROUP_COL])


# In[11]:


feature_names = X_train.columns.tolist()


# In[12]:


# Linux baseline
Linux_fs  = X_test_wFS['FlightSizeLin']
print("Linux ➜  RMSE %.1f   R² %.3f"
      % (root_mean_squared_error(y_test, Linux_fs),
         r2_score(y_test, Linux_fs)))


# In[13]:


# ------------------------------------------------------------------
# 4‑A.  Decision‑Tree  ----------------------------------------------
dt = DecisionTreeRegressor(max_depth=10, random_state=42)
dt.fit(X_train, y_train)


# In[14]:


dt_pred = dt.predict(X_test)
print("Decision Tree ➜  RMSE %.1f   R² %.3f"
      % (root_mean_squared_error(y_test, dt_pred),
         r2_score(y_test, dt_pred)))


# In[15]:


# ------------------------------------------------------------------
# 4‑B.  Random Forest  ----------------------------------------------
rf = RandomForestRegressor(n_estimators=100, n_jobs=-1)
rf.fit(X_train, y_train)


# In[16]:


rf_pred = rf.predict(X_test)
print("Random Forest ➜  RMSE %.1f   R² %.3f"
      % (root_mean_squared_error(y_test, rf_pred),
         r2_score(y_test, rf_pred)))





# In[18]:


# ------------------------------------------------------------------
# 4‑C.  XGBoost  -----------------------------------------------------
xgb = XGBRegressor(
        n_estimators=866, max_depth=8, learning_rate=0.07,
        subsample=0.92, colsample_bytree=0.63,
        objective="reg:squarederror", tree_method="hist",
        eval_metric="rmse", n_jobs=-1, random_state=42)
xgb.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)


# In[19]:


xgb_pred = xgb.predict(X_test)
print("XGBoost       ➜  RMSE %.1f   R² %.3f"
      % (root_mean_squared_error(y_test, xgb_pred),
         r2_score(y_test, xgb_pred)))


# In[20]:


models = {"Random Forest": rf, "XGBoost": xgb, "Decision‑Tree": dt}
# models = {"XGBoost": xgb}


# In[21]:


# -------------------------------
# 6.  5‑Fold Group K‑Fold CV on TRAIN Portion
# -------------------------------
gkf = GroupKFold(n_splits=5)
cv_results = {name: {"rmse": [], "r2": []} for name in models}


# In[22]:


print("\n===== 5‑Fold Group CV on 80% Train Portion =====")
for fold, (tr_idx, val_idx) in enumerate(gkf.split(X_train, y_train, groups=groups_train), start=1):
    X_tr_fold = X_train.iloc[tr_idx]
    y_tr_fold = y_train[tr_idx]
    X_val_fold = X_train.iloc[val_idx]
    y_val_fold = y_train[val_idx]

    for name, model in models.items():
        model.fit(X_tr_fold, y_tr_fold)
        preds = model.predict(X_val_fold)
        rmse_val = np.sqrt(mean_squared_error(y_val_fold, preds))
        r2_val = r2_score(y_val_fold, preds)

        cv_results[name]["rmse"].append(rmse_val)
        cv_results[name]["r2"].append(r2_val)

    print(f" Fold {fold} completed.")
# Print CV results (mean ± std)
for name in models:
    rmse_arr = cv_results[name]["rmse"]
    r2_arr = cv_results[name]["r2"]
    print(
        f"{name:<12} ➜  RMSE {np.mean(rmse_arr):.2f} ± {np.std(rmse_arr):.2f} | "
        f"R² {np.mean(r2_arr):.3f} ± {np.std(r2_arr):.3f}"
    )


# In[23]:


# -------------------------------
# 7.  Retrain on ENTIRE Train Set and Evaluate on Held‑Out Test Set
# -------------------------------
print("\n===== Retrain on Full 80% Train and Evaluate on 20% Test =====")
for name, model in models.items():
    model.fit(X_train, y_train)
    y_pred_test = model.predict(X_test)
    test_rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    test_r2 = r2_score(y_test, y_pred_test)

    print(f"{name:<12} ➜  Test RMSE {test_rmse:.2f} | Test R² {test_r2:.3f}")


# In[24]:


matplotlib.rcParams['pdf.fonttype'] = 42


# In[28]:


# XGBoost importances
booster = xgb.get_booster()
xgb_imp_dict = booster.get_score(importance_type='gain')
# Map to full feature list
xgb_imp = np.array([xgb_imp_dict.get(f, 0) for f in feature_names], dtype=float)
xgb_idx = np.argsort(xgb_imp)[::-1][:10]
plt.figure(figsize=(5,4))
plt.bar(range(10), xgb_imp[xgb_idx])
plt.xticks(range(10), [feature_names[i].replace('status','state') for i in xgb_idx], rotation=25, ha='right')
plt.title("XGBoost – Top 10 Feature Importances")
plt.ylabel("Gain")
plt.tight_layout()
# plt.show()
plt.savefig("xgb2.pdf", bbox_inches='tight', pad_inches=0)
plt.clf()


# In[29]:


# Random Forest importances
rf_imp = rf.feature_importances_
rf_idx = np.argsort(rf_imp)[::-1][:10]
plt.figure(figsize=(5,4))
plt.bar(range(10), rf_imp[rf_idx])
plt.xticks(range(10), [feature_names[i].replace('status','state') for i in rf_idx], rotation=25, ha='right')
plt.title("Random Forest – Top 10 Feature Importances")
plt.ylabel("Gini importance")
plt.tight_layout()
# plt.show()
plt.savefig("rf2.pdf", bbox_inches='tight', pad_inches=0)
plt.clf()


# In[30]:


# DT importances
dt_imp = dt.feature_importances_
dt_idx = np.argsort(dt_imp)[::-1][:10]
plt.figure(figsize=(5,4))
plt.bar(range(10), dt_imp[rf_idx])
plt.xticks(range(10), [feature_names[i] for i in dt_idx], rotation=45, ha='right')
plt.title("Decision Tree – Top 10 Feature Importances")
plt.tight_layout()
# plt.show()
plt.savefig("dt2.pdf")
plt.clf()
