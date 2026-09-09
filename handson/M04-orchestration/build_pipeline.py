"""
モジュール 4: SageMaker Pipelines によるモデル構築パイプライン
------------------------------------------------------------
処理→学習→評価→条件→登録を 1 つの再現可能なパイプラインにまとめます。

  1. TrainingStep: 組み込み XGBoost で学習
  2. ProcessingStep: テストデータで RMSE を評価（evaluate.py）
  3. ConditionStep: RMSE がしきい値以下なら…
  4. RegisterModel: Model Registry に登録

パイプラインパラメータ（instance_type・rmse_threshold）で反復可能性を確保します。
ナレッジチェック対応: しきい値を満たすモデルだけを登録するには「条件ステップ」を使います。

実行:
    python build_pipeline.py            # パイプラインを作成/更新して実行
    python build_pipeline.py --no-run   # 作成/更新のみ（実行しない）
"""

import sys
import os
import argparse
import boto3
import sagemaker
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from sagemaker.processing import ScriptProcessor, ProcessingInput, ProcessingOutput
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.parameters import ParameterString, ParameterFloat
from sagemaker.workflow.steps import TrainingStep, ProcessingStep
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.conditions import ConditionLessThanOrEqualTo
from sagemaker.workflow.functions import JsonGet
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.step_collections import RegisterModel

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, PREFIX, get_role, get_bucket, banner

PIPELINE_NAME = f"{PREFIX}-abalone-pipeline"
MODEL_PACKAGE_GROUP = f"{PREFIX}-abalone-models"
DATA_PREFIX = f"{PREFIX}/abalone"
HERE = os.path.dirname(os.path.abspath(__file__))


def build_pipeline(session, role, bucket):
    image_uri = sagemaker.image_uris.retrieve("xgboost", REGION, version="1.7-1")

    # --- パイプラインパラメータ（実行時に変更可能 = 反復可能性） ---
    training_instance_type = ParameterString(
        name="TrainingInstanceType", default_value="ml.m5.large"
    )
    rmse_threshold = ParameterFloat(name="RmseThreshold", default_value=3.0)

    # --- 1. 学習ステップ ---
    xgb_estimator = Estimator(
        image_uri=image_uri,
        role=role,
        instance_count=1,
        instance_type=training_instance_type,
        output_path=f"s3://{bucket}/{PREFIX}/pipeline/models",
        sagemaker_session=session,
    )
    xgb_estimator.set_hyperparameters(
        objective="reg:squarederror", num_round=100,
        max_depth=5, eta=0.2, subsample=0.7, min_child_weight=6, gamma=4,
    )
    step_train = TrainingStep(
        name="AbaloneTrain",
        estimator=xgb_estimator,
        inputs={
            "train": TrainingInput(
                f"s3://{bucket}/{DATA_PREFIX}/train/", content_type="text/csv"),
            "validation": TrainingInput(
                f"s3://{bucket}/{DATA_PREFIX}/validation/", content_type="text/csv"),
        },
    )

    # --- 2. 評価ステップ ---
    eval_processor = ScriptProcessor(
        image_uri=image_uri,
        command=["python3"],
        instance_type="ml.m5.large",
        instance_count=1,
        base_job_name=f"{PREFIX}-eval",
        role=role,
        sagemaker_session=session,
    )
    evaluation_report = PropertyFile(
        name="EvaluationReport", output_name="evaluation", path="evaluation.json"
    )
    step_eval = ProcessingStep(
        name="AbaloneEval",
        processor=eval_processor,
        inputs=[
            ProcessingInput(
                source=step_train.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model"),
            ProcessingInput(
                source=f"s3://{bucket}/{DATA_PREFIX}/test/test.csv",
                destination="/opt/ml/processing/test"),
        ],
        outputs=[
            ProcessingOutput(
                output_name="evaluation",
                source="/opt/ml/processing/evaluation"),
        ],
        code=os.path.join(HERE, "evaluate.py"),
        property_files=[evaluation_report],
    )

    # --- 4. 登録ステップ ---
    step_register = RegisterModel(
        name="AbaloneRegister",
        estimator=xgb_estimator,
        model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
        content_types=["text/csv"],
        response_types=["text/csv"],
        inference_instances=["ml.m5.large"],
        transform_instances=["ml.m5.large"],
        model_package_group_name=MODEL_PACKAGE_GROUP,
        approval_status="PendingManualApproval",
    )

    # --- 3. 条件ステップ（RMSE <= しきい値 なら登録） ---
    cond = ConditionLessThanOrEqualTo(
        left=JsonGet(
            step_name=step_eval.name,
            property_file=evaluation_report,
            json_path="regression_metrics.rmse.value",
        ),
        right=rmse_threshold,
    )
    step_cond = ConditionStep(
        name="AbaloneRmseCheck",
        conditions=[cond],
        if_steps=[step_register],
        else_steps=[],
    )

    return Pipeline(
        name=PIPELINE_NAME,
        parameters=[training_instance_type, rmse_threshold],
        steps=[step_train, step_eval, step_cond],
        sagemaker_session=session,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-run", action="store_true", help="作成/更新のみ")
    args = parser.parse_args()

    banner("SageMaker Pipelines - モデル構築パイプライン")
    role = get_role()
    bucket = get_bucket()
    session = sagemaker.Session(boto3.session.Session(region_name=REGION))

    pipeline = build_pipeline(session, role, bucket)

    print(f"パイプラインを作成/更新中: {PIPELINE_NAME}")
    pipeline.upsert(role_arn=role)
    print("OK upsert 完了。")

    if args.no_run:
        print("\n--no-run が指定されたため実行しません。")
        print(f"コンソールで確認: SageMaker → Pipelines → {PIPELINE_NAME}")
        return

    print("\nパイプラインを実行中（10〜15 分かかります）...")
    execution = pipeline.start()
    print(f"実行 ARN: {execution.arn}")
    print("完了を待機中...")
    execution.wait(delay=30, max_attempts=60)
    print("\nパイプライン実行完了!")
    for step in execution.list_steps():
        print(f"  {step['StepName']}: {step['StepStatus']}")
    print("\nポイント: 条件ステップにより、RMSE がしきい値以下のモデルだけが")
    print("Model Registry に登録されます（品質ゲート）。")


if __name__ == "__main__":
    main()
