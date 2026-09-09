"""
モジュール 2: アワビ (Abalone) データの取得・前処理・S3 アップロード
--------------------------------------------------------------------
このスクリプトは、後続のトレーニングで使うアワビデータを準備します。

  1. UCI Abalone データセットを SageMaker サンプルバケットから取得
  2. カテゴリ変数 (sex) をワンホット化し、目的変数 (rings) を先頭列に移動
     （SageMaker 組み込み XGBoost は「1 列目が目的変数・ヘッダーなし CSV」を期待）
  3. train / validation / test に分割して S3 にアップロード

出力先: s3://<default-bucket>/mlops-handson/abalone/{train,validation,test}/

実行:
    python prepare_abalone_data.py
"""

import sys
import os
import io
import boto3
import pandas as pd

# handson/ ディレクトリの common.py を import できるようにする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, ABALONE_COLUMNS, get_bucket, banner

DATA_PREFIX = f"{PREFIX}/abalone"


def load_abalone() -> pd.DataFrame:
    """SageMaker サンプルバケットからアワビデータを取得する。"""
    # SageMaker が公開しているサンプルデータ（リージョンごとのバケット）
    src_bucket = f"sagemaker-example-files-prod-{REGION}"
    src_key = "datasets/tabular/uci_abalone/abalone.csv"
    s3 = boto3.client("s3", region_name=REGION)
    print(f"データ取得: s3://{src_bucket}/{src_key}")
    obj = s3.get_object(Bucket=src_bucket, Key=src_key)
    # このサンプル CSV はヘッダーなし。列名を付与する。
    df = pd.read_csv(io.BytesIO(obj["Body"].read()), header=None, names=ABALONE_COLUMNS)
    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """XGBoost 用に前処理する。目的変数(rings)を先頭に、sex をワンホット化。"""
    df = pd.get_dummies(df, columns=["sex"], dtype=int)
    # rings（目的変数）を 1 列目に移動
    cols = ["rings"] + [c for c in df.columns if c != "rings"]
    return df[cols]


def upload_split(df: pd.DataFrame, bucket: str):
    """train/validation/test に分割して S3 にアップロード（ヘッダーなし CSV）。"""
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    n = len(df)
    n_train = int(n * 0.7)
    n_val = int(n * 0.85)
    splits = {
        "train": df.iloc[:n_train],
        "validation": df.iloc[n_train:n_val],
        "test": df.iloc[n_val:],
    }
    s3 = boto3.client("s3", region_name=REGION)
    for name, part in splits.items():
        buf = io.StringIO()
        # test は評価用に目的変数を含めるが、推論入力用には別途特徴量のみも保存
        part.to_csv(buf, header=False, index=False)
        key = f"{DATA_PREFIX}/{name}/{name}.csv"
        s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
        print(f"  OK s3://{bucket}/{key}  ({len(part)} 行)")

    # 推論テスト用に「目的変数を除いた特徴量のみ」の CSV も保存
    features_only = splits["test"].drop(columns=["rings"])
    buf = io.StringIO()
    features_only.to_csv(buf, header=False, index=False)
    key = f"{DATA_PREFIX}/test/test_features.csv"
    s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
    print(f"  OK s3://{bucket}/{key}  (特徴量のみ {len(features_only)} 行)")


def main():
    banner("アワビデータの準備")
    bucket = get_bucket()
    print(f"デフォルトバケット: {bucket}\n")

    df = load_abalone()
    print(f"取得行数: {len(df)}  列: {list(df.columns)}")
    print(df.head(3).to_string(index=False))

    processed = preprocess(df)
    print(f"\n前処理後の列（1 列目が目的変数 rings）: {list(processed.columns)}")

    print("\nS3 にアップロード中...")
    upload_split(processed, bucket)

    print(f"\nデータ準備完了。データプレフィックス: s3://{bucket}/{DATA_PREFIX}/")
    print("次は train_builtin_xgboost.py を実行してトレーニングします。")


if __name__ == "__main__":
    main()
