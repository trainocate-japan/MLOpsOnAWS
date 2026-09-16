"""
モジュール 5: ターゲット追跡オートスケーリング — 設定 → 負荷 → スケールアウト観察
----------------------------------------------------------------------------------
A/B テストのエンドポイント VariantA を対象に、ターゲット追跡ポリシーを設定し、
実際に負荷をかけてスケールアウトを観察します。

  - ScalableDimension = sagemaker:variant:DesiredInstanceCount
  - 予定義メトリクス SageMakerVariantInvocationsPerInstance を使用
  - 目標値を低め（10 invocations/instance/分）に設定し、スケールアウトを起こしやすくする
  - 負荷生成: マルチスレッドで invoke_endpoint を連打
  - DesiredInstanceCount の変化をポーリングして確認

先に `python ab_test_variants.py` でエンドポイントを作成してください。

実行:
    python autoscaling_demo.py           # 設定 → 負荷 → スケールアウト観察
    python autoscaling_demo.py --delete  # 登録解除
"""

import sys
import os
import argparse
import time
import threading
import boto3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, banner

ENDPOINT_NAME = f"{PREFIX}-abalone-ab"
VARIANT = "VariantA"
RESOURCE_ID = f"endpoint/{ENDPOINT_NAME}/variant/{VARIANT}"
POLICY_NAME = f"{PREFIX}-target-tracking"

# スケールアウトを起こしやすくするため目標値を低めに設定
TARGET_VALUE = 10.0          # 1 インスタンスあたり分間 10 呼び出しを目標
MIN_CAPACITY = 1
MAX_CAPACITY = 4
SCALE_OUT_COOLDOWN = 60      # スケールアウトのクールダウン（秒）
SCALE_IN_COOLDOWN = 300      # スケールインのクールダウン（秒）

# 負荷生成の設定
LOAD_THREADS = 4             # 並行スレッド数
LOAD_DURATION_SEC = 180      # 負荷をかける時間（秒）
LOAD_SLEEP = 0.05            # 各呼び出し間の待機（秒）
OBSERVE_INTERVAL = 15        # インスタンス数チェック間隔（秒）
OBSERVE_TIMEOUT = 360        # スケールアウトを待つ最大時間（秒）

# 推論テスト用データ（特徴量のみ 1 行。sex ワンホット: F=1,I=0,M=0）
SAMPLE_PAYLOAD = "0.45,0.35,0.12,0.55,0.24,0.11,0.15,1,0,0"


def configure_autoscaling():
    """ターゲット追跡ポリシーを設定する。"""
    sm = boto3.client("sagemaker", region_name=REGION)
    try:
        status = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)["EndpointStatus"]
    except sm.exceptions.ClientError:
        print(f"エンドポイント {ENDPOINT_NAME} が見つかりません。")
        print("先に `python ab_test_variants.py` を実行してください。")
        return False
    print(f"対象エンドポイント: {ENDPOINT_NAME}（{status}）")
    print(f"対象バリアント: {VARIANT}")

    aas = boto3.client("application-autoscaling", region_name=REGION)

    # 1. スケーラブルターゲットを登録
    aas.register_scalable_target(
        ServiceNamespace="sagemaker",
        ResourceId=RESOURCE_ID,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        MinCapacity=MIN_CAPACITY,
        MaxCapacity=MAX_CAPACITY,
    )
    print(f"\n[1/2] スケーラブルターゲット登録（min={MIN_CAPACITY}, max={MAX_CAPACITY}）")

    # 2. ターゲット追跡ポリシーを設定
    aas.put_scaling_policy(
        PolicyName=POLICY_NAME,
        ServiceNamespace="sagemaker",
        ResourceId=RESOURCE_ID,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        PolicyType="TargetTrackingScaling",
        TargetTrackingScalingPolicyConfiguration={
            "TargetValue": TARGET_VALUE,
            "PredefinedMetricSpecification": {
                "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance",
            },
            "ScaleInCooldown": SCALE_IN_COOLDOWN,
            "ScaleOutCooldown": SCALE_OUT_COOLDOWN,
        },
    )
    print(f"[2/2] ターゲット追跡ポリシー設定")
    print(f"      メトリクス: SageMakerVariantInvocationsPerInstance")
    print(f"      目標値: {TARGET_VALUE} invocations/instance/分")
    print(f"      スケールアウト クールダウン: {SCALE_OUT_COOLDOWN}秒")
    print(f"      スケールイン クールダウン: {SCALE_IN_COOLDOWN}秒")
    return True


def generate_load():
    """マルチスレッドで invoke_endpoint を連打し、負荷を発生させる。"""
    banner("負荷生成 → スケールアウト観察")
    print(f"設定: {LOAD_THREADS} スレッド × {LOAD_DURATION_SEC}秒間")
    print(f"      各スレッドは {LOAD_SLEEP}秒間隔で invoke_endpoint を呼び出します")
    print()

    sm = boto3.client("sagemaker", region_name=REGION)
    smr = boto3.client("sagemaker-runtime", region_name=REGION)

    # 現在のインスタンス数を確認
    initial_count = _get_instance_count(sm)
    print(f"現在のインスタンス数: {initial_count}")
    print()

    # 負荷生成スレッドを起動
    stop_event = threading.Event()
    invoke_count = [0]  # ミュータブルでスレッド間共有
    lock = threading.Lock()

    def _invoke_loop():
        client = boto3.client("sagemaker-runtime", region_name=REGION)
        while not stop_event.is_set():
            try:
                client.invoke_endpoint(
                    EndpointName=ENDPOINT_NAME,
                    ContentType="text/csv",
                    Body=SAMPLE_PAYLOAD,
                    TargetVariant=VARIANT,
                )
                with lock:
                    invoke_count[0] += 1
            except Exception:
                pass  # エンドポイント更新中の一時エラーは無視
            time.sleep(LOAD_SLEEP)

    threads = []
    for i in range(LOAD_THREADS):
        t = threading.Thread(target=_invoke_loop, daemon=True)
        t.start()
        threads.append(t)
    print(f"負荷生成開始（{LOAD_THREADS} スレッド起動）")

    # インスタンス数をポーリングしながらスケールアウトを待つ
    start_time = time.time()
    scaled = False
    last_count_display = 0

    while time.time() - start_time < OBSERVE_TIMEOUT:
        elapsed = int(time.time() - start_time)
        current_count = _get_instance_count(sm)
        with lock:
            total_invokes = invoke_count[0]

        # 進捗表示
        print(f"  [{elapsed:>3}秒経過] インスタンス数: {current_count}  "
              f"累計呼び出し: {total_invokes}回", flush=True)

        if current_count > initial_count:
            print(f"\n{'='*50}")
            print(f"  スケールアウト検出: {initial_count} → {current_count} インスタンス")
            print(f"{'='*50}")
            scaled = True
            break

        # 負荷生成の時間が過ぎたらスレッドを止めて、もう少し待つ
        if elapsed >= LOAD_DURATION_SEC and not stop_event.is_set():
            stop_event.set()
            print(f"\n  負荷生成を停止（{LOAD_DURATION_SEC}秒経過）。"
                  "メトリクス反映を待機中...")

        time.sleep(OBSERVE_INTERVAL)

    # 停止
    stop_event.set()
    for t in threads:
        t.join(timeout=5)

    with lock:
        total_invokes = invoke_count[0]

    if not scaled:
        print(f"\n{OBSERVE_TIMEOUT}秒以内にスケールアウトが確認できませんでした。")
        print("CloudWatch メトリクスの反映に時間がかかることがあります。")
        print("以下のコマンドで手動確認できます:")
        print(f"  aws cloudwatch get-metric-statistics \\")
        print(f"    --namespace AWS/SageMaker \\")
        print(f"    --metric-name InvocationsPerInstance \\")
        print(f"    --dimensions Name=EndpointName,Value={ENDPOINT_NAME} "
              f"Name=VariantName,Value={VARIANT} \\")
        print(f"    --start-time $(date -u -d '10 minutes ago' +%Y-%m-%dT%H:%M:%SZ) \\")
        print(f"    --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \\")
        print(f"    --period 60 --statistics Sum --region {REGION}")

    print(f"\n合計呼び出し回数: {total_invokes}")

    # スケーリングアクティビティを表示
    _show_scaling_activities()


def _get_instance_count(sm):
    """エンドポイントの対象バリアントの現在のインスタンス数を返す。"""
    desc = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)
    for v in desc.get("ProductionVariants", []):
        if v["VariantName"] == VARIANT:
            return v.get("CurrentInstanceCount", v.get("DesiredInstanceCount", 1))
    return 1


def _show_scaling_activities():
    """Application Auto Scaling のスケーリングアクティビティを表示する。"""
    aas = boto3.client("application-autoscaling", region_name=REGION)
    activities = aas.describe_scaling_activities(
        ServiceNamespace="sagemaker",
        ResourceId=RESOURCE_ID,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        MaxResults=5,
    ).get("ScalingActivities", [])

    if activities:
        print("\n直近のスケーリングアクティビティ:")
        for a in activities:
            print(f"  [{a['StatusCode']}] {a.get('Description', 'N/A')}")
            print(f"    原因: {a.get('Cause', 'N/A')[:120]}")
    else:
        print("\nスケーリングアクティビティはまだ記録されていません。")


def delete():
    """オートスケーリングの登録を解除する。"""
    banner("オートスケーリングの登録解除")
    aas = boto3.client("application-autoscaling", region_name=REGION)

    # ポリシーを削除
    try:
        aas.delete_scaling_policy(
            PolicyName=POLICY_NAME,
            ServiceNamespace="sagemaker",
            ResourceId=RESOURCE_ID,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        )
        print(f"OK ポリシー削除: {POLICY_NAME}")
    except aas.exceptions.ObjectNotFoundException:
        print(f"-- ポリシーが見つかりません（スキップ）: {POLICY_NAME}")

    # スケーラブルターゲットを登録解除
    try:
        aas.deregister_scalable_target(
            ServiceNamespace="sagemaker",
            ResourceId=RESOURCE_ID,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        )
        print(f"OK 登録解除: {RESOURCE_ID}")
    except aas.exceptions.ObjectNotFoundException:
        print(f"-- スケーラブルターゲットが見つかりません（スキップ）")


def main():
    banner("ターゲット追跡オートスケーリング")

    parser = argparse.ArgumentParser(
        description="ターゲット追跡オートスケーリングの設定・負荷テスト・削除")
    parser.add_argument("--delete", action="store_true",
                        help="オートスケーリング設定を削除")
    parser.add_argument("--configure-only", action="store_true",
                        help="ポリシー設定のみ（負荷生成しない）")
    args = parser.parse_args()

    if args.delete:
        delete()
    elif args.configure_only:
        configure_autoscaling()
        print("\nポリシーを設定しました。負荷テストは手動で行ってください。")
        print("削除: python autoscaling_demo.py --delete")
    else:
        if configure_autoscaling():
            print()
            generate_load()
            print("\nポイント:")
            print("  - 負荷が目標値を超えると CloudWatch アラームが発火し、")
            print("    Auto Scaling がインスタンスを追加（スケールアウト）します。")
            print("  - 負荷が収まるとクールダウン後にインスタンスを削減（スケールイン）します。")
            print("  - 他のスケーリング方法: ステップスケーリング / スケジュールスケーリング")
            print("\n削除: python autoscaling_demo.py --delete")


if __name__ == "__main__":
    main()
