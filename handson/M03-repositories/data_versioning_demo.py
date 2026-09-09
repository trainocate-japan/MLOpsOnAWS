"""
モジュール 3: S3 バージョニングによるデータのバージョン管理
----------------------------------------------------------
データのバージョニングは再現性とデータドリフト検知の基盤です。
このスクリプトは SageMaker のデフォルトバケットで S3 バージョニングを有効化し、
同じキーにデータを 2 回アップロードして複数バージョンが保持されることを確認します。

  - バージョニング有効化により、同じオブジェクトの変更履歴が保持される
  - 「どのモデルがどのバージョンのデータで学習されたか」を追跡できる

実行:
    python data_versioning_demo.py
"""

import sys
import os
import boto3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, get_bucket, banner

KEY = f"{PREFIX}/versioning-demo/abalone_snapshot.csv"


def main():
    banner("S3 データバージョニング")
    bucket = get_bucket()
    s3 = boto3.client("s3", region_name=REGION)

    # バージョニングを有効化
    status = s3.get_bucket_versioning(Bucket=bucket).get("Status")
    print(f"バケット: {bucket}  現在のバージョニング: {status or '無効'}")
    if status != "Enabled":
        s3.put_bucket_versioning(
            Bucket=bucket, VersioningConfiguration={"Status": "Enabled"}
        )
        print("OK バージョニングを有効化しました。")

    # 同じキーに 2 バージョンをアップロード（データの更新をシミュレート）
    print("\nデータの v1 と v2 をアップロード...")
    s3.put_object(Bucket=bucket, Key=KEY,
                  Body=b"length,diameter,rings\n0.45,0.35,10\n")
    s3.put_object(Bucket=bucket, Key=KEY,
                  Body=b"length,diameter,rings\n0.45,0.35,10\n0.52,0.41,12\n")

    # バージョン一覧を確認
    versions = s3.list_object_versions(Bucket=bucket, Prefix=KEY).get("Versions", [])
    print(f"\n{KEY} のバージョン数: {len(versions)}")
    for v in versions:
        latest = " (最新)" if v["IsLatest"] else ""
        print(f"  VersionId={v['VersionId'][:16]}...  "
              f"size={v['Size']}B{latest}")

    print("\nポイント: データをバージョン管理すると、過去の学習を再現でき、")
    print("データドリフト検知（M06）のベースラインとしても使えます。")
    print("→ Feature Store（feature_store_demo.py）は event_time により")
    print("  特徴量レベルでの時系列バージョン管理を提供します。")


if __name__ == "__main__":
    main()
