"""
モジュール 5: 本番バリアントによる A/B テスト
----------------------------------------------
1 つのエンドポイントに 2 つの本番バリアント（現行モデル A / 新モデル B）を配置し、
トラフィックを加重ルーティングして比較します。

  - InitialVariantWeight でトラフィック配分を指定（例: A=50%, B=50%）
  - invoke 時に TargetVariant を指定すれば特定バリアントだけを呼び出せる
  - 両バリアントとも実際の応答を返す点がシャドーテストとの違い

このデモでは同じモデルアーティファクトを 2 つのバリアントとして使います
（実際には B に新しいモデルを配置します）。

実行:
    python ab_test_variants.py           # デプロイ + A/B 呼び出し
    python ab_test_variants.py --delete  # 削除
"""

import sys
import os
import argparse
import time
import boto3
import sagemaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, get_role, banner

ENDPOINT_NAME = f"{PREFIX}-abalone-ab"
CONFIG_NAME = f"{PREFIX}-abalone-ab-config"
MODEL_A = f"{PREFIX}-abalone-model-a"
MODEL_B = f"{PREFIX}-abalone-model-b"


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
    banner("A/B テスト（本番バリアント）")
    role = get_role()
    sm = boto3.client("sagemaker", region_name=REGION)
    artifact = latest_artifact(sm)
    image_uri = sagemaker.image_uris.retrieve("xgboost", REGION, version="1.7-1")

    # 2 つのモデル（デモのため同じアーティファクトを A / B に使用）
    for name in (MODEL_A, MODEL_B):
        try:
            sm.create_model(
                ModelName=name, ExecutionRoleArn=role,
                PrimaryContainer={"Image": image_uri, "ModelDataUrl": artifact},
            )
            print(f"OK モデル作成: {name}")
        except sm.exceptions.ClientError:
            print(f"-- モデル既存: {name}")

    # 2 つの本番バリアント（各 50%）
    print("\nエンドポイント設定（VariantA=50%, VariantB=50%）を作成...")
    _recreate_config(sm, [
        {"VariantName": "VariantA", "ModelName": MODEL_A,
         "InitialInstanceCount": 1, "InstanceType": "ml.m5.large",
         "InitialVariantWeight": 1.0},
        {"VariantName": "VariantB", "ModelName": MODEL_B,
         "InitialInstanceCount": 1, "InstanceType": "ml.m5.large",
         "InitialVariantWeight": 1.0},
    ])
    _create_or_update_endpoint(sm)
    _wait_in_service(sm)

    # 加重ルーティングで呼び出し（どちらのバリアントが応答したか確認）
    smr = boto3.client("sagemaker-runtime", region_name=REGION)
    sample = "0.45,0.35,0.12,0.55,0.24,0.11,0.15,1,0,0"
    print("\n加重ルーティングで 6 回呼び出し:")
    counts = {}
    for _ in range(6):
        resp = smr.invoke_endpoint(
            EndpointName=ENDPOINT_NAME, ContentType="text/csv", Body=sample)
        v = resp["ResponseMetadata"]["HTTPHeaders"].get(
            "x-amzn-invoked-production-variant", "unknown")
        counts[v] = counts.get(v, 0) + 1
    print(f"  応答したバリアントの内訳: {counts}")

    # 特定バリアントを直接指定して呼び出し
    resp = smr.invoke_endpoint(
        EndpointName=ENDPOINT_NAME, ContentType="text/csv",
        Body=sample, TargetVariant="VariantB")
    print(f"\n  TargetVariant=VariantB を直接指定 → 予測 = "
          f"{resp['Body'].read().decode().strip()}")
    print("\nポイント: A/B テストは両モデルの実応答をトラフィック配分で比較します。")
    print("削除: python ab_test_variants.py --delete")


def _recreate_config(sm, variants):
    try:
        sm.delete_endpoint_config(EndpointConfigName=CONFIG_NAME)
    except sm.exceptions.ClientError:
        pass
    sm.create_endpoint_config(
        EndpointConfigName=CONFIG_NAME, ProductionVariants=variants)


def _create_or_update_endpoint(sm):
    try:
        sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
        sm.update_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=CONFIG_NAME)
        print("エンドポイントを更新中...")
    except sm.exceptions.ClientError:
        sm.create_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=CONFIG_NAME)
        print("エンドポイントを作成中...")


def _wait_in_service(sm):
    print("InService を待機中...", end="", flush=True)
    while True:
        s = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)["EndpointStatus"]
        if s == "InService":
            print(" 完了"); return
        if s == "Failed":
            raise RuntimeError("エンドポイント作成失敗")
        print(".", end="", flush=True); time.sleep(15)


def delete():
    banner("A/B テストリソースの削除")
    sm = boto3.client("sagemaker", region_name=REGION)
    for fn, k in [
        (sm.delete_endpoint, {"EndpointName": ENDPOINT_NAME}),
        (sm.delete_endpoint_config, {"EndpointConfigName": CONFIG_NAME}),
        (sm.delete_model, {"ModelName": MODEL_A}),
        (sm.delete_model, {"ModelName": MODEL_B}),
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
