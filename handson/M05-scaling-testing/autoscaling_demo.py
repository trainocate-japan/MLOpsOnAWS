"""
モジュール 5: ターゲット追跡オートスケーリングの設定
----------------------------------------------------
既存のエンドポイントのバリアントを Application Auto Scaling のスケーラブルターゲット
として登録し、ターゲット追跡ポリシーを設定します。

  - ScalableDimension = sagemaker:variant:DesiredInstanceCount
  - 予定義メトリクス SageMakerVariantInvocationsPerInstance を使用
  - 1 インスタンスあたりの分間呼び出し数を目標値に保つようにスケール

このスクリプトは A/B テストのエンドポイント（VariantA）を対象にします。
先に `python ab_test_variants.py` でエンドポイントを作成してください。

実行:
    python autoscaling_demo.py           # スケーリング設定
    python autoscaling_demo.py --delete  # 登録解除
"""

import sys
import os
import argparse
import boto3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, banner

ENDPOINT_NAME = f"{PREFIX}-abalone-ab"
VARIANT = "VariantA"
RESOURCE_ID = f"endpoint/{ENDPOINT_NAME}/variant/{VARIANT}"
POLICY_NAME = f"{PREFIX}-target-tracking"


def configure():
    banner("ターゲット追跡オートスケーリング")
    sm = boto3.client("sagemaker", region_name=REGION)
    try:
        status = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)["EndpointStatus"]
    except sm.exceptions.ClientError:
        print(f"エンドポイント {ENDPOINT_NAME} が見つかりません。")
        print("先に `python ab_test_variants.py` を実行してください。")
        return
    print(f"対象エンドポイント: {ENDPOINT_NAME}（{status}） バリアント: {VARIANT}")

    aas = boto3.client("application-autoscaling", region_name=REGION)

    # 1. スケーラブルターゲットを登録（最小 1・最大 4 インスタンス）
    aas.register_scalable_target(
        ServiceNamespace="sagemaker",
        ResourceId=RESOURCE_ID,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        MinCapacity=1,
        MaxCapacity=4,
    )
    print("OK スケーラブルターゲット登録（min=1, max=4）")

    # 2. ターゲット追跡ポリシーを設定
    aas.put_scaling_policy(
        PolicyName=POLICY_NAME,
        ServiceNamespace="sagemaker",
        ResourceId=RESOURCE_ID,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        PolicyType="TargetTrackingScaling",
        TargetTrackingScalingPolicyConfiguration={
            "TargetValue": 70.0,  # 1 インスタンスあたり分間 70 呼び出しを目標
            "PredefinedMetricSpecification": {
                "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
            },
            "ScaleInCooldown": 300,
            "ScaleOutCooldown": 60,
        },
    )
    print("OK ターゲット追跡ポリシー設定（目標: 70 invocations/instance/分）")
    print("\nポイント: 負荷が増えると自動でインスタンスを増やし、")
    print("落ち着くとクールダウン後に減らします（コスト最適化）。")
    print("他のスケーリング方法: ステップスケーリング / スケジュールスケーリング / オンデマンド")
    print("削除: python autoscaling_demo.py --delete")


def delete():
    banner("オートスケーリングの登録解除")
    aas = boto3.client("application-autoscaling", region_name=REGION)
    try:
        aas.deregister_scalable_target(
            ServiceNamespace="sagemaker",
            ResourceId=RESOURCE_ID,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        )
        print(f"OK 登録解除: {RESOURCE_ID}")
    except aas.exceptions.ObjectNotFoundException:
        print("-- スケーラブルターゲットが見つかりません（スキップ）")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true")
    args = parser.parse_args()
    delete() if args.delete else configure()


if __name__ == "__main__":
    main()
