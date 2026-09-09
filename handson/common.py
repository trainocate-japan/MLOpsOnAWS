"""
共通ユーティリティ
------------------
すべてのモジュールで共有する設定・ヘルパー関数をまとめています。

  - REGION: 使用リージョン（デフォルト us-east-1、AWS_REGION 環境変数で上書き可）
  - PREFIX: リソース名のプレフィックス（mlops-handson）
  - get_role(): SageMaker 実行ロール ARN を解決する
      1. 環境変数 SAGEMAKER_ROLE_ARN（EC2 デモ環境で自動設定）
      2. sagemaker.get_execution_role()（SageMaker Studio 内）
  - get_bucket(): 資材保存用の S3 バケット（SageMaker のデフォルトバケット）
"""

import os
import boto3

REGION = os.environ.get("AWS_REGION", "us-east-1")
PREFIX = "mlops-handson"

# アワビ (Abalone) データセットの列名（UCI Abalone / SageMaker サンプル）
# 目的変数 = rings（年齢の指標）。回帰で予測します。
ABALONE_COLUMNS = [
    "sex", "length", "diameter", "height",
    "whole_weight", "shucked_weight", "viscera_weight", "shell_weight",
    "rings",
]


def get_role() -> str:
    """SageMaker 実行ロール ARN を解決する。"""
    role = os.environ.get("SAGEMAKER_ROLE_ARN")
    if role:
        return role
    try:
        import sagemaker
        return sagemaker.get_execution_role()
    except Exception as e:
        raise ValueError(
            "SAGEMAKER_ROLE_ARN が設定されていません。\n"
            "EC2 デモ環境以外で実行する場合は、次を実行してください:\n"
            "  export SAGEMAKER_ROLE_ARN=arn:aws:iam::<ACCOUNT_ID>:role/MLOpsHandsonSageMakerRole\n"
            f"（元のエラー: {e}）"
        )


def get_account_id() -> str:
    return boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]


def get_bucket() -> str:
    """SageMaker のデフォルトバケット名を返す（なければ作成される）。"""
    import sagemaker
    session = sagemaker.Session(boto3.session.Session(region_name=REGION))
    return session.default_bucket()


def banner(title: str) -> None:
    print("=" * 66)
    print(f" {title}")
    print("=" * 66)
