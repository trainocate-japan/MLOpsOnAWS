"""
モジュール 5: シャドーバリアントテスト
--------------------------------------
本番バリアント（現行モデル）に加えて、シャドーバリアント（新モデル）を配置します。
SageMaker は本番トラフィックのコピーをシャドーバリアントに送りますが、
その応答はユーザーに返しません（ユーザー影響ゼロで新モデルを評価）。

  - ProductionVariants: 100% の応答を返す本番バリアント（1 つ）
  - ShadowProductionVariants: トラフィックの複製を受けるシャドーバリアント（1 つ）
  - 制約: シャドー使用時は本番 1・シャドー 1 のみ。サーバーレス/非同期/MME/MCE とは併用不可。

実行:
    python shadow_test.py           # デプロイ + 呼び出し
    python shadow_test.py --delete  # 削除
"""

import sys
import os
import argparse
import time
import boto3
import sagemaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, get_role, banner

ENDPOINT_NAME = f"{PREFIX}-abalone-shadow"
CONFIG_NAME = f"{PREFIX}-abalone-shadow-config"
MODEL_PROD = f"{PREFIX}-abalone-model-prod"
MODEL_SHADOW = f"{PREFIX}-abalone-model-shadow"


def latest_artifact(sm):
    jobs = sm.list_training_jobs(
        NameContains=PREFIX, StatusEquals="Completed",
        SortBy="CreationTime", SortOrder="Descending", MaxResults=1,
    ).get("TrainingJobSummaries", [])
    if not jobs:
        raise RuntimeError("完了済みトレーニングジョブがありません。先に M02 を実行してください。")
    return sm.describe_training_job(
        TrainingJobName=jobs[0]["TrainingJobName"]
    )["ModelArtifacts"]["S3ModelArtifacts"]


def deploy():
    banner("シャドーバリアントテスト")
    role = get_role()
    sm = boto3.client("sagemaker", region_name=REGION)
    artifact = latest_artifact(sm)
    image_uri = sagemaker.image_uris.retrieve("xgboost", REGION, version="1.7-1")

    for name in (MODEL_PROD, MODEL_SHADOW):
        try:
            sm.create_model(
                ModelName=name, ExecutionRoleArn=role,
                PrimaryContainer={"Image": image_uri, "ModelDataUrl": artifact})
            print(f"OK モデル作成: {name}")
        except sm.exceptions.ClientError:
            print(f"-- モデル既存: {name}")

    print("\n本番バリアント + シャドーバリアントの設定を作成...")
    try:
        sm.delete_endpoint_config(EndpointConfigName=CONFIG_NAME)
    except sm.exceptions.ClientError:
        pass
    sm.create_endpoint_config(
        EndpointConfigName=CONFIG_NAME,
        ProductionVariants=[{
            "VariantName": "Production", "ModelName": MODEL_PROD,
            "InitialInstanceCount": 1, "InstanceType": "ml.m5.large",
            "InitialVariantWeight": 1.0,
        }],
        ShadowProductionVariants=[{
            "VariantName": "Shadow", "ModelName": MODEL_SHADOW,
            "InitialInstanceCount": 1, "InstanceType": "ml.m5.large",
            "InitialVariantWeight": 1.0,
        }],
    )

    try:
        sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
        sm.update_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=CONFIG_NAME)
        print("エンドポイントを更新中...")
    except sm.exceptions.ClientError:
        sm.create_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=CONFIG_NAME)
        print("エンドポイントを作成中...")

    print("InService を待機中...", end="", flush=True)
    while True:
        s = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)["EndpointStatus"]
        if s == "InService":
            print(" 完了"); break
        if s == "Failed":
            raise RuntimeError("エンドポイント作成失敗")
        print(".", end="", flush=True); time.sleep(15)

    smr = boto3.client("sagemaker-runtime", region_name=REGION)
    sample = "0.45,0.35,0.12,0.55,0.24,0.11,0.15,1,0,0"
    print("\n本番バリアントへ 3 回呼び出し（シャドーには自動で複製が送られる）:")
    for _ in range(3):
        resp = smr.invoke_endpoint(
            EndpointName=ENDPOINT_NAME, ContentType="text/csv", Body=sample)
        print(f"  本番応答（ユーザーに返る）= {resp['Body'].read().decode().strip()}")
    print("→ シャドーの応答は返りません。CloudWatch でシャドーのメトリクスを比較できます。")
    print("\nポイント: シャドーテストはユーザー影響ゼロで新モデルの運用性能を検証します。")
    print("削除: python shadow_test.py --delete")


def delete():
    banner("シャドーテストリソースの削除")
    sm = boto3.client("sagemaker", region_name=REGION)
    for fn, k in [
        (sm.delete_endpoint, {"EndpointName": ENDPOINT_NAME}),
        (sm.delete_endpoint_config, {"EndpointConfigName": CONFIG_NAME}),
        (sm.delete_model, {"ModelName": MODEL_PROD}),
        (sm.delete_model, {"ModelName": MODEL_SHADOW}),
    ]:
        try:
            fn(**k); print(f"OK 削除: {list(k.values())[0]}")
        except sm.exceptions.ClientError as e:
            print(f"-- スキップ: {e.response['Error']['Message']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true")
    args = parser.parse_args()
    delete() if args.delete else deploy()


if __name__ == "__main__":
    main()
