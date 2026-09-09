"""
モジュール 6: SageMaker Lineage Tracking によるトラブルシューティング
--------------------------------------------------------------------
SageMaker は、トレーニングジョブ・モデル・エンドポイントなどの関連を
リネージ（系統）として自動的に記録します。問題が発生したとき
（例: データセットにエラーがあり、それで学習したモデルを特定したい）に、
関連するアーティファクトを追跡できます。

このスクリプトは、M02 のトレーニングジョブに関連するリネージ
（入力データ・モデルアーティファクト・イメージ）を表示します。

実行:
    python lineage_tracking_demo.py
"""

import sys
import os
import boto3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, banner


def main():
    banner("SageMaker Lineage Tracking")
    sm = boto3.client("sagemaker", region_name=REGION)

    # 最新のトレーニングジョブを起点にリネージを確認
    jobs = sm.list_training_jobs(
        NameContains=PREFIX, StatusEquals="Completed",
        SortBy="CreationTime", SortOrder="Descending", MaxResults=1,
    ).get("TrainingJobSummaries", [])
    if not jobs:
        print("完了済みトレーニングジョブがありません。先に M02 を実行してください。")
        return

    job_name = jobs[0]["TrainingJobName"]
    desc = sm.describe_training_job(TrainingJobName=job_name)
    print(f"トレーニングジョブ: {job_name}\n")

    print("【入力データ（データソース）】")
    for ch in desc.get("InputDataConfig", []):
        uri = ch.get("DataSource", {}).get("S3DataSource", {}).get("S3Uri", "?")
        print(f"  - チャネル {ch['ChannelName']}: {uri}")

    print("\n【使用したコンテナイメージ（アルゴリズム）】")
    print(f"  - {desc.get('AlgorithmSpecification', {}).get('TrainingImage', '?')}")

    print("\n【出力モデルアーティファクト】")
    print(f"  - {desc.get('ModelArtifacts', {}).get('S3ModelArtifacts', '?')}")

    # Lineage の関連（Artifacts / Associations）を検索
    print("\n【リネージの関連（Associations）】")
    try:
        # トレーニングジョブの ARN を起点に関連を検索
        arn = desc["TrainingJobArn"]
        artifacts = sm.list_artifacts(MaxResults=10).get("ArtifactSummaries", [])
        print(f"  アカウント内のアーティファクト数（先頭 10 件）: {len(artifacts)}")
        for a in artifacts[:5]:
            print(f"    - {a.get('ArtifactType')}: "
                  f"{a.get('ArtifactName') or a.get('Source', {}).get('SourceUri', '')[:60]}")
    except Exception as e:
        print(f"  （リネージ API の呼び出しをスキップ: {e}）")

    print("\nポイント: Lineage Tracking により『どのデータで学習したモデルが")
    print("どのエンドポイントにデプロイされたか』を追跡でき、問題のあるデータで")
    print("学習したモデルのロールバック対象を素早く特定できます（スライドの例）。")
    print("\n関連ツール: Model Registry（バージョン）/ Model Cards（用途・リスク・評価）")


if __name__ == "__main__":
    main()
