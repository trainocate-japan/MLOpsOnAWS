"""
モジュール 3: SageMaker Feature Store（特徴量の共有・バージョン管理）
--------------------------------------------------------------------
アワビの特徴量を Feature Group として登録し、オンライン/オフラインストアに
取り込みます。Feature Store により特徴量が「信頼できる唯一の情報源」となり、
チーム間で再利用でき、学習と推論で一貫した特徴量を使えます。

  - record identifier: レコードを一意に識別する列（abalone_id）
  - event time: 各レコードのタイムスタンプ列（特徴量の時系列バージョン管理に使う）
  - オンラインストア: 低レイテンシーのリアルタイム取得
  - オフラインストア: S3 上の履歴データ（学習・バッチに使う）

実行:
    python feature_store_demo.py
"""

import sys
import os
import io
import time
import boto3
import pandas as pd
import sagemaker
from sagemaker.feature_store.feature_group import FeatureGroup

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, ABALONE_COLUMNS, get_role, get_bucket, banner

FEATURE_GROUP_NAME = f"{PREFIX}-abalone-features"
DATA_PREFIX = f"{PREFIX}/abalone"


def load_sample(bucket: str) -> pd.DataFrame:
    """M02 で作成した train データの一部を特徴量として読み込む。"""
    s3 = boto3.client("s3", region_name=REGION)
    key = f"{DATA_PREFIX}/train/train.csv"
    obj = s3.get_object(Bucket=bucket, Key=key)
    # M02 で rings を先頭に移動し sex をワンホット化済み。列名を復元する。
    df = pd.read_csv(io.BytesIO(obj["Body"].read()), header=None)
    cols = ["rings", "length", "diameter", "height", "whole_weight",
            "shucked_weight", "viscera_weight", "shell_weight",
            "sex_F", "sex_I", "sex_M"]
    df.columns = cols[: df.shape[1]]
    df = df.head(100).copy()
    # Feature Store に必要な識別子とイベント時刻を追加
    df.insert(0, "abalone_id", range(len(df)))
    df["event_time"] = float(round(time.time(), 3))
    return df


def main():
    banner("SageMaker Feature Store")
    role = get_role()
    bucket = get_bucket()
    session = sagemaker.Session(boto3.session.Session(region_name=REGION))

    df = load_sample(bucket)
    print(f"特徴量サンプル {len(df)} 行、列: {list(df.columns)}")

    fg = FeatureGroup(name=FEATURE_GROUP_NAME, sagemaker_session=session)
    # DataFrame から特徴量定義（スキーマ）を自動生成
    fg.load_feature_definitions(data_frame=df)

    existing = session.boto_session.client("sagemaker").list_feature_groups(
        NameContains=FEATURE_GROUP_NAME
    ).get("FeatureGroupSummaries", [])
    if any(f["FeatureGroupName"] == FEATURE_GROUP_NAME for f in existing):
        print(f"Feature Group は既に存在します: {FEATURE_GROUP_NAME}（作成をスキップ）")
    else:
        print("Feature Group を作成中...")
        fg.create(
            s3_uri=f"s3://{bucket}/{PREFIX}/feature-store",
            record_identifier_name="abalone_id",
            event_time_feature_name="event_time",
            role_arn=role,
            enable_online_store=True,
        )
        _wait_created(fg)

    print("\n特徴量を取り込み中 (ingest)...")
    fg.ingest(data_frame=df, max_workers=2, wait=True)
    print(f"OK {len(df)} 件の特徴量レコードを取り込みました。")

    # オンラインストアから 1 件取得して確認
    rec = session.boto_session.client("sagemaker-featurestore-runtime").get_record(
        FeatureGroupName=FEATURE_GROUP_NAME, RecordIdentifierValueAsString="0"
    )
    print("\nオンラインストアから abalone_id=0 を取得:")
    for f in rec.get("Record", [])[:5]:
        print(f"  {f['FeatureName']} = {f['ValueAsString']}")

    print("\nポイント: Feature Store により特徴量が再利用可能な"
          "『信頼できる唯一の情報源』になります。")
    print("→ cleanup_all.sh で Feature Group を削除できます。")


def _wait_created(fg: FeatureGroup):
    print("  作成完了を待機中...", end="", flush=True)
    while True:
        status = fg.describe().get("FeatureGroupStatus")
        if status == "Created":
            print(" 完了")
            return
        if status in ("CreateFailed", "DeleteFailed"):
            raise RuntimeError(f"Feature Group 作成失敗: {status}")
        print(".", end="", flush=True)
        time.sleep(5)


if __name__ == "__main__":
    main()
