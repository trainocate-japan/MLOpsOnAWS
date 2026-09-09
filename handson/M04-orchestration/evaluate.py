"""
モジュール 4: パイプラインの評価ステップ用スクリプト
----------------------------------------------------
このスクリプトは SageMaker Pipelines の ProcessingStep（評価）内で実行されます。
学習済みモデル (model.tar.gz) とテストデータを読み込み、RMSE を計算して
evaluation.json に書き出します。この JSON を条件ステップが参照します。

SageMaker Processing の標準パス:
  - モデル:     /opt/ml/processing/model/model.tar.gz
  - テストデータ: /opt/ml/processing/test/
  - 出力:       /opt/ml/processing/evaluation/evaluation.json
"""

import json
import os
import tarfile
import glob
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_squared_error

MODEL_DIR = "/opt/ml/processing/model"
TEST_DIR = "/opt/ml/processing/test"
OUTPUT_DIR = "/opt/ml/processing/evaluation"


def main():
    # model.tar.gz を展開
    tar_path = os.path.join(MODEL_DIR, "model.tar.gz")
    with tarfile.open(tar_path) as tar:
        tar.extractall(path=MODEL_DIR)

    booster = xgb.Booster()
    # 組み込み XGBoost は "xgboost-model" という名前で保存する
    model_files = glob.glob(os.path.join(MODEL_DIR, "*model*"))
    model_file = next((f for f in model_files if not f.endswith(".tar.gz")), None)
    booster.load_model(model_file)

    # テストデータ（1 列目が目的変数 rings）
    test_files = glob.glob(os.path.join(TEST_DIR, "*.csv"))
    df = pd.concat([pd.read_csv(f, header=None) for f in test_files], ignore_index=True)
    y_true, X = df.iloc[:, 0], df.iloc[:, 1:]

    preds = booster.predict(xgb.DMatrix(X))
    rmse = float(mean_squared_error(y_true, preds) ** 0.5)
    print(f"評価結果 RMSE = {rmse:.4f}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report = {"regression_metrics": {"rmse": {"value": rmse}}}
    with open(os.path.join(OUTPUT_DIR, "evaluation.json"), "w") as f:
        json.dump(report, f)


if __name__ == "__main__":
    main()
