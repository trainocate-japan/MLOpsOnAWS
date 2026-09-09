"""
モジュール 6: Model Monitor のベースライン作成と監視スケジュール
----------------------------------------------------------------
学習データからベースライン（統計と制約）を生成し、キャプチャデータと比較する
データ品質モニタリングを時間ごとにスケジュールします。

  1. DefaultModelMonitor でベースライン処理ジョブを実行
     - statistics.json（各特徴量の統計）
     - constraints.json（期待される制約）
  2. create_monitoring_schedule で 1 時間ごとの監視を設定
     - キャプチャデータをベースラインと比較し、制約違反（ドリフト）を検出

前提: enable_data_capture.py でエンドポイントを作成済みであること。

実行:
    python model_monitor_baseline.py           # ベースライン + スケジュール作成
    python model_monitor_baseline.py --delete   # スケジュール削除
"""

import sys
import os
import io
import argparse
import boto3
import pandas as pd
import sagemaker
from sagemaker.model_monitor import DefaultModelMonitor, CronExpressionGenerator
from sagemaker.model_monitor.dataset_format import DatasetFormat

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, get_role, get_bucket, banner

ENDPOINT_NAME = f"{PREFIX}-abalone-monitored"
SCHEDULE_NAME = f"{PREFIX}-abalone-dq-schedule"
DATA_PREFIX = f"{PREFIX}/abalone"


def prepare_baseline_csv(bucket) -> str:
    """ベースライン用に、ヘッダー付きの特徴量 CSV を用意する。
    Model Monitor のベースラインはヘッダー付き CSV を推奨。"""
    s3 = boto3.client("s3", region_name=REGION)
    obj = s3.get_object(Bucket=bucket, Key=f"{DATA_PREFIX}/train/train.csv")
    df = pd.read_csv(io.BytesIO(obj["Body"].read()), header=None)
    cols = ["rings", "length", "diameter", "height", "whole_weight",
            "shucked_weight", "viscera_weight", "shell_weight",
            "sex_F", "sex_I", "sex_M"]
    df.columns = cols[: df.shape[1]]
    # 目的変数を除いた特徴量のみをベースラインにする（推論入力と揃える）
    features = df.drop(columns=["rings"])
    buf = io.StringIO()
    features.to_csv(buf, index=False)
    key = f"{PREFIX}/monitor/baseline/baseline.csv"
    s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
    return f"s3://{bucket}/{key}"


def create():
    banner("Model Monitor - ベースラインと監視スケジュール")
    role = get_role()
    bucket = get_bucket()
    session = sagemaker.Session(boto3.session.Session(region_name=REGION))

    baseline_uri = prepare_baseline_csv(bucket)
    baseline_results = f"s3://{bucket}/{PREFIX}/monitor/baseline-results"
    print(f"ベースライン入力: {baseline_uri}")

    monitor = DefaultModelMonitor(
        role=role,
        instance_count=1,
        instance_type="ml.m5.large",
        volume_size_in_gb=20,
        max_runtime_in_seconds=1800,
        sagemaker_session=session,
    )

    print("\nベースライン処理ジョブを実行中（数分かかります）...")
    monitor.suggest_baseline(
        baseline_dataset=baseline_uri,
        dataset_format=DatasetFormat.csv(header=True),
        output_s3_uri=baseline_results,
        wait=True,
    )
    print(f"OK ベースライン生成: {baseline_results}")
    print("  - statistics.json（統計） / constraints.json（制約）")

    print("\n監視スケジュールを作成中（1 時間ごと）...")
    monitor.create_monitoring_schedule(
        monitor_schedule_name=SCHEDULE_NAME,
        endpoint_input=ENDPOINT_NAME,
        output_s3_uri=f"s3://{bucket}/{PREFIX}/monitor/reports",
        statistics=monitor.baseline_statistics(),
        constraints=monitor.suggested_constraints(),
        schedule_cron_expression=CronExpressionGenerator.hourly(),
        enable_cloudwatch_metrics=True,
    )
    print(f"OK 監視スケジュール作成: {SCHEDULE_NAME}")
    print("\nポイント: キャプチャデータをベースラインと比較し、制約違反（ドリフト）を")
    print("時間ごとに検出します。CloudWatch メトリクスでアラームも設定できます。")
    print("注意: スケジュールは定期的にインスタンスを起動します。完了後は削除してください。")
    print("削除: python model_monitor_baseline.py --delete")


def delete():
    banner("監視スケジュールの削除")
    sm = boto3.client("sagemaker", region_name=REGION)
    try:
        sm.delete_monitoring_schedule(MonitoringScheduleName=SCHEDULE_NAME)
        print(f"OK 削除: {SCHEDULE_NAME}")
    except sm.exceptions.ClientError as e:
        print(f"-- スキップ: {e.response['Error']['Message']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true")
    args = parser.parse_args()
    delete() if args.delete else create()


if __name__ == "__main__":
    main()
