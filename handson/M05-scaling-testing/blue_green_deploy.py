"""
モジュール 5: ブルー/グリーンデプロイ（トラフィックシフト）
----------------------------------------------------------
既存エンドポイントを新しいエンドポイント設定に更新する際、ブルー/グリーンの
トラフィックシフト（Canary / Linear）でリスクを抑えて切り替えます。

  - update_endpoint の DeploymentConfig.BlueGreenUpdatePolicy を使用
  - Canary: 一部を先行させ、ベイク期間の監視後に残りをシフト
  - Linear: 一定割合ずつ等間隔でシフト
  - 自動ロールバック: CloudWatch アラームでベイク期間中に問題を検知したら旧環境へ戻す

このデモは、まず初期エンドポイントを作成し、次に Canary トラフィックシフトで
同じ設定に更新して、ブルー/グリーンの仕組みを確認します。

実行:
    python blue_green_deploy.py           # 初期デプロイ + Canary 更新
    python blue_green_deploy.py --delete  # 削除
"""

import sys
import os
import argparse
import time
import boto3
import sagemaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, get_role, banner

ENDPOINT_NAME = f"{PREFIX}-abalone-bluegreen"
CONFIG_V1 = f"{PREFIX}-abalone-bg-v1"
CONFIG_V2 = f"{PREFIX}-abalone-bg-v2"
MODEL_NAME = f"{PREFIX}-abalone-model-bg"


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


def _config(sm, name, model):
    try:
        sm.delete_endpoint_config(EndpointConfigName=name)
    except sm.exceptions.ClientError:
        pass
    sm.create_endpoint_config(
        EndpointConfigName=name,
        ProductionVariants=[{
            "VariantName": "AllTraffic", "ModelName": model,
            "InitialInstanceCount": 1, "InstanceType": "ml.m5.large",
            "InitialVariantWeight": 1.0,
        }],
    )


def _wait(sm):
    print("待機中...", end="", flush=True)
    while True:
        s = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)["EndpointStatus"]
        if s == "InService":
            print(" InService"); return
        if s == "Failed":
            raise RuntimeError("エンドポイント失敗")
        print(".", end="", flush=True); time.sleep(15)


def deploy():
    banner("ブルー/グリーンデプロイ（Canary トラフィックシフト）")
    role = get_role()
    sm = boto3.client("sagemaker", region_name=REGION)
    artifact = latest_artifact(sm)
    image_uri = sagemaker.image_uris.retrieve("xgboost", REGION, version="1.7-1")

    try:
        sm.create_model(
            ModelName=MODEL_NAME, ExecutionRoleArn=role,
            PrimaryContainer={"Image": image_uri, "ModelDataUrl": artifact})
        print(f"OK モデル作成: {MODEL_NAME}")
    except sm.exceptions.ClientError:
        print(f"-- モデル既存: {MODEL_NAME}")

    # 初期（ブルー）デプロイ
    _config(sm, CONFIG_V1, MODEL_NAME)
    try:
        sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
        print("エンドポイントは既存です。")
    except sm.exceptions.ClientError:
        print("初期エンドポイント（ブルー）を作成中...")
        sm.create_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=CONFIG_V1)
        _wait(sm)

    # グリーン（新設定）へ Canary トラフィックシフトで更新
    _config(sm, CONFIG_V2, MODEL_NAME)
    print("\nCanary トラフィックシフトでグリーンへ更新中...")
    sm.update_endpoint(
        EndpointName=ENDPOINT_NAME,
        EndpointConfigName=CONFIG_V2,
        DeploymentConfig={
            "BlueGreenUpdatePolicy": {
                "TrafficRoutingConfiguration": {
                    "Type": "CANARY",
                    "CanarySize": {"Type": "CAPACITY_PERCENT", "Value": 50},
                    "WaitIntervalInSeconds": 120,  # ベイク期間
                },
                "TerminationWaitInSeconds": 120,
                "MaximumExecutionTimeoutInSeconds": 1800,
            },
        },
    )
    _wait(sm)
    print("\nポイント: Canary は一部（50%）を先行させ、ベイク期間の監視後に")
    print("残りをシフトします。Linear は一定割合ずつ等間隔でシフトします。")
    print("CloudWatch アラームと組み合わせると自動ロールバックが可能です。")
    print("削除: python blue_green_deploy.py --delete")


def delete():
    banner("ブルー/グリーンリソースの削除")
    sm = boto3.client("sagemaker", region_name=REGION)
    for fn, k in [
        (sm.delete_endpoint, {"EndpointName": ENDPOINT_NAME}),
        (sm.delete_endpoint_config, {"EndpointConfigName": CONFIG_V1}),
        (sm.delete_endpoint_config, {"EndpointConfigName": CONFIG_V2}),
        (sm.delete_model, {"ModelName": MODEL_NAME}),
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
