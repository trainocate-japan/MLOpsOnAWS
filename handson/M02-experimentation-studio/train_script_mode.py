"""
モジュール 2: スクリプトモード (BYOS) でのトレーニング
------------------------------------------------------
AWS 管理の XGBoost コンテナに、自分のトレーニングスクリプト (abalone_train.py) を
持ち込んで学習します（Bring Your Own Script）。

ポイント:
  - コンテナイメージは AWS 管理（フレームワークは XGBoost）
  - entry_point に自分のスクリプトを指定するだけで独自ロジックを実行できる
  - requirements.txt を同梱すれば追加パッケージもインストール可能
  - 組み込みアルゴリズムモードとの違い: 学習ロジックを完全に制御できる

実行:
    python train_script_mode.py
"""

import sys
import os
import boto3
import sagemaker
from sagemaker.xgboost.estimator import XGBoost
from sagemaker.inputs import TrainingInput

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, get_role, get_bucket, banner

DATA_PREFIX = f"{PREFIX}/abalone"
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    banner("スクリプトモード (BYOS) でのトレーニング")
    role = get_role()
    bucket = get_bucket()
    session = sagemaker.Session(boto3.session.Session(region_name=REGION))

    output_path = f"s3://{bucket}/{PREFIX}/models/script-mode-xgboost"

    # XGBoost をフレームワークとして使用（entry_point に自分のスクリプト）
    estimator = XGBoost(
        entry_point="abalone_train.py",
        source_dir=HERE,
        framework_version="1.7-1",
        role=role,
        instance_count=1,
        instance_type="ml.m5.large",
        output_path=output_path,
        sagemaker_session=session,
        base_job_name=f"{PREFIX}-xgb-byos",
        hyperparameters={
            "num_round": 100,
            "max_depth": 5,
            "eta": 0.2,
            "subsample": 0.7,
        },
    )

    train_input = TrainingInput(
        f"s3://{bucket}/{DATA_PREFIX}/train/", content_type="text/csv"
    )
    val_input = TrainingInput(
        f"s3://{bucket}/{DATA_PREFIX}/validation/", content_type="text/csv"
    )

    print("\nトレーニングジョブを開始します（数分かかります）...")
    print("→ AWS 管理の XGBoost コンテナ内で abalone_train.py が実行されます。")
    estimator.fit({"train": train_input, "validation": val_input})

    print("\nトレーニング完了!")
    print(f"モデルアーティファクト: {estimator.model_data}")
    print("\nポイント: 組み込みアルゴリズムモードと同じ SageMaker の仕組みで、")
    print("学習ロジックだけを自分のスクリプトに差し替えられました（BYOS）。")


if __name__ == "__main__":
    main()
