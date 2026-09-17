"""
モジュール 6: データドリフトを発生させるトラフィック生成
--------------------------------------------------------
ベースラインの分布から意図的にずらした入力をエンドポイントに送り、
データドリフトをシミュレートします。これにより、次回の監視ジョブで
制約違反（ドリフト）が検出されるようになります。

  - 通常の測定値を大きく外れた値（極端に大きいアワビ）を送信
  - キャプチャされたデータが次の監視ジョブでベースラインと比較される

前提: enable_data_capture.py のエンドポイントが起動していること。

実行:
    python generate_drift_traffic.py
"""

import sys
import os
import time
import random
import boto3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, banner

ENDPOINT_NAME = f"{PREFIX}-abalone-monitored"


def main():
    banner("データドリフトのシミュレーション")
    smr = boto3.client("sagemaker-runtime", region_name=REGION)
    sm = boto3.client("sagemaker", region_name=REGION)

    try:
        status = sm.describe_endpoint(EndpointName=ENDPOINT_NAME)["EndpointStatus"]
    except sm.exceptions.ClientError:
        print(f"エンドポイント {ENDPOINT_NAME} が見つかりません。")
        print("先に `python enable_data_capture.py` を実行してください。")
        return
    print(f"対象エンドポイント: {ENDPOINT_NAME}（{status}）")

    print("\nドリフトした入力（ベースラインより大幅に大きい測定値）を 30 回送信...")
    for i in range(30):
        # 通常の length は 0.1〜0.8 程度。ここでは 1.5〜2.5 と大きくずらす。
        length = round(random.uniform(1.5, 2.5), 3)
        diameter = round(length * 0.8, 3)
        height = round(length * 0.3, 3)
        ww = round(length * 2.0, 3)
        sw = round(ww * 0.4, 3)
        vw = round(ww * 0.2, 3)
        shw = round(ww * 0.3, 3)
        # sex はワンホット（ここでは M=1 に固定）
        row = f"{length},{diameter},{height},{ww},{sw},{vw},{shw},0,0,1"
        smr.invoke_endpoint(EndpointName=ENDPOINT_NAME,
                            ContentType="text/csv", Body=row)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1} 件送信")
        time.sleep(0.3)

    print("\nOK ドリフトトラフィックの送信完了。")
    print("送信した入力はエンドポイントのデータキャプチャ機能で S3 に保存されます。")
    print("キャプチャデータの確認（数分後に現れます）:")
    bucket_hint = f"s3://<default-bucket>/{PREFIX}/monitor/datacapture/{ENDPOINT_NAME}/"
    print(f"  aws s3 ls {bucket_hint} --recursive --region {REGION}")
    print("")
    print("このドリフトデータを model_monitor_baseline.py で生成した")
    print("constraints.json（各特徴量の期待レンジ）と突き合わせると、")
    print("length などが期待レンジを大きく外れている＝ドリフトだと分かります。")
    print("")
    print("※ SageMaker Model Monitor は 2026-06-30 付でメンテナンスモードに移行し、")
    print("  新規顧客は監視スケジュールを作成できません。定期監視が必要な場合は、")
    print("  キャプチャデータと constraints.json を比較する処理を自前のジョブ")
    print("  （Processing / Lambda + EventBridge）として実装します。")
    print("  参照: https://docs.aws.amazon.com/general/latest/gr/maintenance_services.html")
    print("\nポイント: ドリフトを検知したら、再学習（イベント駆動/スケジュール/オンデマンド）")
    print("や手動介入で対処します。")


if __name__ == "__main__":
    main()
