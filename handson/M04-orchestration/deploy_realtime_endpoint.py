"""
モジュール 4: リアルタイム推論エンドポイントのデプロイ
------------------------------------------------------
M02 で学習したアワビモデルを SageMaker のリアルタイムエンドポイントとして
デプロイし、推論を実行します。

  - Model → EndpointConfig → Endpoint の 3 段階（SageMaker がインフラを管理）
  - リアルタイムエンドポイントは常時稼働（低レイテンシーの同期推論）
  - 注意: エンドポイントは起動中ずっと課金されます。完了後は削除してください。

実行:
    python deploy_realtime_endpoint.py           # デプロイ + 推論テスト
    python deploy_realtime_endpoint.py --delete  # エンドポイントを削除
"""

import sys
import os
import argparse
import boto3
import sagemaker
from sagemaker.model import Model

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, get_role, banner

ENDPOINT_NAME = f"{PREFIX}-abalone-rt"


def find_latest_model_artifact(sm) -> str:
    jobs = sm.list_training_jobs(
        NameContains=PREFIX, StatusEquals="Completed",
        SortBy="CreationTime", SortOrder="Descending", MaxResults=1,
    ).get("TrainingJobSummaries", [])
    if not jobs:
        raise RuntimeError("完了済みトレーニングジョブがありません。先に M02 を実行してください。")
    desc = sm.describe_training_job(TrainingJobName=jobs[0]["TrainingJobName"])
    return desc["ModelArtifacts"]["S3ModelArtifacts"]


def deploy():
    banner("リアルタイムエンドポイントのデプロイ")
    role = get_role()
    session = sagemaker.Session(boto3.session.Session(region_name=REGION))
    sm = boto3.client("sagemaker", region_name=REGION)

    artifact = find_latest_model_artifact(sm)
    image_uri = sagemaker.image_uris.retrieve("xgboost", REGION, version="1.7-1")
    print(f"モデルアーティファクト: {artifact}")

    model = Model(
        image_uri=image_uri,
        model_data=artifact,
        role=role,
        sagemaker_session=session,
        name=f"{PREFIX}-abalone-model",
    )

    print(f"\nエンドポイントをデプロイ中: {ENDPOINT_NAME}（数分かかります）...")
    predictor = model.deploy(
        initial_instance_count=1,
        instance_type="ml.m5.large",
        endpoint_name=ENDPOINT_NAME,
    )
    print("OK エンドポイントが InService になりました。")

    # 推論テスト（特徴量のみ 1 行。sex はワンホット: F=1,I=0,M=0）
    sample = "0.45,0.35,0.12,0.55,0.24,0.11,0.15,1,0,0"
    smr = boto3.client("sagemaker-runtime", region_name=REGION)
    resp = smr.invoke_endpoint(
        EndpointName=ENDPOINT_NAME, ContentType="text/csv", Body=sample
    )
    pred = resp["Body"].read().decode().strip()
    print(f"\n推論テスト: 入力={sample}")
    print(f"予測された輪紋数 (rings) = {pred}")
    print("\n注意: エンドポイントは起動中ずっと課金されます。")
    print(f"削除: python deploy_realtime_endpoint.py --delete")


def delete():
    banner("リアルタイムエンドポイントの削除")
    sm = boto3.client("sagemaker", region_name=REGION)
    for fn, kwargs in [
        (sm.delete_endpoint, {"EndpointName": ENDPOINT_NAME}),
        (sm.delete_endpoint_config, {"EndpointConfigName": ENDPOINT_NAME}),
    ]:
        try:
            fn(**kwargs)
            print(f"OK 削除: {list(kwargs.values())[0]}")
        except sm.exceptions.ClientError as e:
            print(f"-- スキップ: {e.response['Error']['Message']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true")
    args = parser.parse_args()
    delete() if args.delete else deploy()


if __name__ == "__main__":
    main()
