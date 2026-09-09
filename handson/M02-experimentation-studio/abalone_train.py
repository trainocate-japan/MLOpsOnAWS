"""
モジュール 2: BYOS 用トレーニングスクリプト（スクリプトモードで実行される）
--------------------------------------------------------------------------
このスクリプトは SageMaker の XGBoost コンテナ内で実行されます（BYOS）。
SageMaker は環境変数とコマンドライン引数で入出力パスを渡します。

  - 入力データ: SM_CHANNEL_TRAIN / SM_CHANNEL_VALIDATION（コンテナ内のローカルパス）
  - モデル出力: SM_MODEL_DIR（ここに保存したものが model.tar.gz になる）
  - ハイパーパラメータ: コマンドライン引数として渡される

SageMaker 標準フォルダ構造（スライド「SageMaker 標準フォルダ」対応）に従います。
"""

import argparse
import os
import pandas as pd
import xgboost as xgb


def load_csv(channel_dir: str) -> pd.DataFrame:
    """チャネルディレクトリ内の CSV（ヘッダーなし・1 列目が目的変数）を読み込む。"""
    files = [os.path.join(channel_dir, f) for f in os.listdir(channel_dir)
             if f.endswith(".csv")]
    frames = [pd.read_csv(f, header=None) for f in files]
    return pd.concat(frames, ignore_index=True)


def main():
    parser = argparse.ArgumentParser()
    # ハイパーパラメータ（SageMaker がコマンドライン引数として渡す）
    parser.add_argument("--num_round", type=int, default=100)
    parser.add_argument("--max_depth", type=int, default=5)
    parser.add_argument("--eta", type=float, default=0.2)
    parser.add_argument("--subsample", type=float, default=0.7)
    # SageMaker 標準の環境変数（入出力パス）
    parser.add_argument("--model_dir", type=str,
                        default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    parser.add_argument("--train", type=str,
                        default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    parser.add_argument("--validation", type=str,
                        default=os.environ.get("SM_CHANNEL_VALIDATION", "/opt/ml/input/data/validation"))
    args = parser.parse_args()

    train_df = load_csv(args.train)
    val_df = load_csv(args.validation)

    # 1 列目が目的変数 (rings)、残りが特徴量
    y_train, X_train = train_df.iloc[:, 0], train_df.iloc[:, 1:]
    y_val, X_val = val_df.iloc[:, 0], val_df.iloc[:, 1:]

    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)

    params = {
        "objective": "reg:squarederror",
        "max_depth": args.max_depth,
        "eta": args.eta,
        "subsample": args.subsample,
        "eval_metric": "rmse",
    }

    print(f"学習開始: num_round={args.num_round}, params={params}")
    booster = xgb.train(
        params,
        dtrain,
        num_boost_round=args.num_round,
        evals=[(dtrain, "train"), (dval, "validation")],
        verbose_eval=10,
    )

    # SM_MODEL_DIR に保存したものが model.tar.gz として S3 に出力される
    os.makedirs(args.model_dir, exist_ok=True)
    model_path = os.path.join(args.model_dir, "xgboost-model")
    booster.save_model(model_path)
    print(f"モデルを保存しました: {model_path}")


if __name__ == "__main__":
    main()
