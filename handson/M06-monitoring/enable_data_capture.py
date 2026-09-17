"""
モジュール 6: データキャプチャ付きエンドポイントのデプロイ
----------------------------------------------------------
Model Monitor でドリフトを検知するには、まずエンドポイントの入力/出力を
S3 にキャプチャする必要があります。

  - DataCaptureConfig で入力(Input)と出力(Output)をキャプチャ
  - InitialSamplingPercentage でサンプリング率を指定（コスト削減のため）
  - キャプチャ先: s3://<bucket>/mlops-handson/monitor/datacapture/

実行:
    python enable_data_capture.py           # デプロイ + テスト推論
    python enable_data_capture.py --delete   # 削除
"""

import sys
import os
import argparse
import time
import boto3
import sagemaker
from sagemaker.model import Model
from sagemaker.model_monitor import DataCaptureConfig

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, get_role, get_bucket, banner

ENDPOINT_NAME = f"{PREFIX}-abalone-monitored"


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
    banner("データキャプチャ付きエンドポイント")
    role = get_role()
    bucket = get_bucket()
    session = sagemaker.Session(boto3.session.Session(region_name=REGION))
    sm = boto3.client("sagemaker", region_name=REGION)

    artifact = latest_artifact(sm)
    image_uri = sagemaker.image_uris.retrieve("xgboost", REGION, version="1.7-1")
    capture_uri = f"s3://{bucket}/{PREFIX}/monitor/datacapture"

    model = Model(
        image_uri=image_uri, model_data=artifact, role=role,
        sagemaker_session=session, name=f"{PREFIX}-abalone-monitored-model",
    )

    # データキャプチャ設定（入力と出力を 100% キャプチャ）
    # sagemaker_session を明示的に渡す。渡さないと内部で引数なしの Session() が
    # 生成され、リージョン未解決で "Must setup local AWS configuration ..." エラーになる。
    capture_config = DataCaptureConfig(
        enable_capture=True,
        sampling_percentage=100,
        destination_s3_uri=capture_uri,
        sagemaker_session=session,
    )

    print(f"エンドポイントをデプロイ中: {ENDPOINT_NAME}...")
    print(f"キャプチャ先: {capture_uri}")
    model.deploy(
        initial_instance_count=1,
        instance_type="ml.m5.large",
        endpoint_name=ENDPOINT_NAME,
        data_capture_config=capture_config,
    )
    print("OK InService")

    # 通常のトラフィック（ベースライン相当の分布）を送る
    smr = boto3.client("sagemaker-runtime", region_name=REGION)
    sample = "0.45,0.35,0.12,0.55,0.24,0.11,0.15,1,0,0"
    print("\n通常トラフィックを 10 回送信（キャプチャされます）...")
    for _ in range(10):
        smr.invoke_endpoint(EndpointName=ENDPOINT_NAME,
                            ContentType="text/csv", Body=sample)
        time.sleep(0.5)
    print("OK 送信完了。数分後、キャプチャデータが S3 に現れます:")
    print(f"  aws s3 ls {capture_uri}/{ENDPOINT_NAME}/ --recursive")
    print("\n次は model_monitor_baseline.py でベースラインと監視スケジュールを作成します。")
    print("削除: python enable_data_capture.py --delete")


def delete():
    banner("監視エンドポイントの削除")
    sm = boto3.client("sagemaker", region_name=REGION)
    for fn, k in [
        (sm.delete_endpoint, {"EndpointName": ENDPOINT_NAME}),
        (sm.delete_endpoint_config, {"EndpointConfigName": ENDPOINT_NAME}),
        (sm.delete_model, {"ModelName": f"{PREFIX}-abalone-monitored-model"}),
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
