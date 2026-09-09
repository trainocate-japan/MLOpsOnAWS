"""
モジュール 2: 組み込み XGBoost アルゴリズムでのトレーニング（アルゴリズムモード）
------------------------------------------------------------------------------
SageMaker の組み込み XGBoost アルゴリズムを使って、アワビの輪紋数 (rings) を
回帰予測するモデルを学習します。

ポイント:
  - image_uris.retrieve で AWS 管理の XGBoost コンテナイメージ URI を取得
  - SageMaker がトレーニング用に Docker コンテナを自動で起動する（BYOS/BYOC でも同じ仕組み）
  - 学習結果は S3 に model.tar.gz として出力される（モデルアーティファクト）
  - objective=reg:squarederror（回帰）

実行:
    python train_builtin_xgboost.py
"""

import sys
import os
import boto3
import sagemaker
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, get_role, get_bucket, banner

DATA_PREFIX = f"{PREFIX}/abalone"


def main():
    banner("組み込み XGBoost でのトレーニング")
    role = get_role()
    bucket = get_bucket()
    session = sagemaker.Session(boto3.session.Session(region_name=REGION))

    # 組み込み XGBoost のコンテナイメージ URI を取得（バージョンを明示）
    image_uri = sagemaker.image_uris.retrieve("xgboost", REGION, version="1.7-1")
    print(f"XGBoost コンテナイメージ: {image_uri}")

    output_path = f"s3://{bucket}/{PREFIX}/models/builtin-xgboost"

    estimator = Estimator(
        image_uri=image_uri,
        role=role,
        instance_count=1,
        instance_type="ml.m5.large",
        output_path=output_path,
        sagemaker_session=session,
        base_job_name=f"{PREFIX}-xgb",
    )

    # 回帰タスクのハイパーパラメータ（アワビの輪紋数を予測）
    estimator.set_hyperparameters(
        objective="reg:squarederror",
        num_round=100,
        max_depth=5,
        eta=0.2,
        subsample=0.7,
        min_child_weight=6,
        gamma=4,
    )

    train_input = TrainingInput(
        f"s3://{bucket}/{DATA_PREFIX}/train/", content_type="text/csv"
    )
    val_input = TrainingInput(
        f"s3://{bucket}/{DATA_PREFIX}/validation/", content_type="text/csv"
    )

    print("\nトレーニングジョブを開始します（数分かかります）...")
    print("→ SageMaker が XGBoost コンテナを起動し、S3 のデータで学習します。")
    estimator.fit({"train": train_input, "validation": val_input})

    print("\nトレーニング完了!")
    print(f"モデルアーティファクト: {estimator.model_data}")
    print("\nこの model.tar.gz が後続モジュール（デプロイ・登録・監視）で使われます。")
    print("ヒント: このパスをメモしておくか、次のコマンドで確認できます:")
    print(f'  aws sagemaker describe-training-job --training-job-name '
          f'{estimator.latest_training_job.name} --region {REGION} '
          f'--query "ModelArtifacts.S3ModelArtifacts" --output text')


if __name__ == "__main__":
    main()
