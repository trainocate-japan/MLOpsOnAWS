"""
モジュール 3: SageMaker Model Registry（モデルのカタログ化・バージョン管理・承認）
--------------------------------------------------------------------------------
M02 で学習したモデルアーティファクトを Model Registry に登録します。

  1. Model Package Group を作成（モデルの「フォルダ」。バージョンをまとめる）
  2. モデルバージョン（Model Package）を登録（承認待ち状態で作成）
  3. 承認ステータスを PendingManualApproval → Approved に更新
  4. バージョン一覧を表示

Model Registry はモデルのバージョン管理・コラボレーション・ガバナンスを提供します。

実行:
    python model_registry_demo.py
"""

import sys
import os
import boto3
import sagemaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, get_role, banner

MODEL_PACKAGE_GROUP = f"{PREFIX}-abalone-models"


def find_latest_model_artifact(sm) -> str:
    """M02 のトレーニングジョブから最新のモデルアーティファクト S3 URI を取得。"""
    jobs = sm.list_training_jobs(
        NameContains=PREFIX, StatusEquals="Completed",
        SortBy="CreationTime", SortOrder="Descending", MaxResults=1,
    ).get("TrainingJobSummaries", [])
    if not jobs:
        raise RuntimeError(
            "完了したトレーニングジョブが見つかりません。"
            "先に M02 の train_builtin_xgboost.py を実行してください。"
        )
    name = jobs[0]["TrainingJobName"]
    desc = sm.describe_training_job(TrainingJobName=name)
    artifact = desc["ModelArtifacts"]["S3ModelArtifacts"]
    print(f"最新トレーニングジョブ: {name}")
    print(f"モデルアーティファクト: {artifact}")
    return artifact


def main():
    banner("SageMaker Model Registry")
    role = get_role()  # noqa: F841 (登録自体には未使用だが前提確認)
    sm = boto3.client("sagemaker", region_name=REGION)

    artifact = find_latest_model_artifact(sm)
    image_uri = sagemaker.image_uris.retrieve("xgboost", REGION, version="1.7-1")

    # 1. Model Package Group を作成（冪等）
    groups = sm.list_model_package_groups(
        NameContains=MODEL_PACKAGE_GROUP
    ).get("ModelPackageGroupSummaryList", [])
    if any(g["ModelPackageGroupName"] == MODEL_PACKAGE_GROUP for g in groups):
        print(f"\nModel Package Group は既に存在します: {MODEL_PACKAGE_GROUP}")
    else:
        sm.create_model_package_group(
            ModelPackageGroupName=MODEL_PACKAGE_GROUP,
            ModelPackageGroupDescription="アワビ年齢予測モデルのカタログ",
            Tags=[
                {"Key": "project", "Value": "abalone"},
                {"Key": "team", "Value": "mlops-handson"},
            ],
        )
        print(f"\nOK Model Package Group を作成: {MODEL_PACKAGE_GROUP}")

    # 2. モデルバージョンを登録（承認待ち状態）
    print("\nモデルバージョンを登録中...")
    resp = sm.create_model_package(
        ModelPackageGroupName=MODEL_PACKAGE_GROUP,
        ModelPackageDescription="XGBoost アワビ回帰モデル",
        ModelApprovalStatus="PendingManualApproval",
        InferenceSpecification={
            "Containers": [{"Image": image_uri, "ModelDataUrl": artifact}],
            "SupportedContentTypes": ["text/csv"],
            "SupportedResponseMIMETypes": ["text/csv"],
            "SupportedRealtimeInferenceInstanceTypes": ["ml.m5.large"],
            "SupportedTransformInstanceTypes": ["ml.m5.large"],
        },
    )
    package_arn = resp["ModelPackageArn"]
    print(f"OK 登録完了（承認待ち）: {package_arn}")

    # 3. 承認ステータスを Approved に更新
    print("\n承認ステータスを Approved に更新中...")
    sm.update_model_package(
        ModelPackageArn=package_arn,
        ModelApprovalStatus="Approved",
    )
    print("OK 承認済み (Approved) に更新しました。")

    # 4. バージョン一覧を表示
    print("\nModel Package Group 内のバージョン:")
    pkgs = sm.list_model_packages(
        ModelPackageGroupName=MODEL_PACKAGE_GROUP,
        SortBy="CreationTime", SortOrder="Descending",
    ).get("ModelPackageSummaryList", [])
    for p in pkgs:
        print(f"  v{p['ModelPackageVersion']}  "
              f"{p['ModelApprovalStatus']}  {p['ModelPackageArn']}")

    print("\nポイント: Model Registry はバージョン管理・承認ワークフロー・"
          "ガバナンスを提供します。承認済みモデルだけを本番にデプロイします。")


if __name__ == "__main__":
    main()
