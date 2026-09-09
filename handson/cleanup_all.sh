#!/bin/bash
# =============================================================================
# MLOps Engineering on AWS - 全リソース一括削除スクリプト
# 各モジュールのハンズオンで作成した AWS リソースを削除します。
# スクリプトは冪等です（存在しないリソースはスキップします）。
# 命名規則: すべてのリソースは "mlops-handson" プレフィックスを使用します。
# =============================================================================

REGION="${AWS_REGION:-us-east-1}"
PREFIX="mlops-handson"

echo "=============================================="
echo " ハンズオンリソース クリーンアップ"
echo " リージョン: $REGION"
echo "=============================================="
echo ""
echo "  対象アカウント:"
aws sts get-caller-identity --query "Account" --output text
echo ""
read -r -p "  上記アカウントのリソースを削除します。続行しますか？ (y/N): " ANSWER
if [ "$ANSWER" != "y" ] && [ "$ANSWER" != "Y" ]; then
    echo "  中止しました。"
    exit 0
fi
echo ""

# =============================================================================
# エンドポイント（M04 / M05 / M06）: 起動中は課金されるため最優先で削除
# =============================================================================
echo "----------------------------------------------"
echo " [M04/M05/M06] SageMaker エンドポイントの削除"
echo "----------------------------------------------"
EP_NAMES=$(aws sagemaker list-endpoints --region "$REGION" \
    --query "Endpoints[?starts_with(EndpointName, '$PREFIX')].EndpointName" \
    --output text 2>/dev/null || echo "")
for EP in $EP_NAMES; do
    aws sagemaker delete-endpoint --endpoint-name "$EP" --region "$REGION" >/dev/null 2>&1 && \
        echo "  OK エンドポイント削除: $EP" || echo "  WARN エンドポイント削除失敗: $EP"
done
[ -z "$EP_NAMES" ] && echo "  -- エンドポイントなし（スキップ）"

# エンドポイント設定の削除
EPC_NAMES=$(aws sagemaker list-endpoint-configs --region "$REGION" \
    --query "EndpointConfigs[?starts_with(EndpointConfigName, '$PREFIX')].EndpointConfigName" \
    --output text 2>/dev/null || echo "")
for EPC in $EPC_NAMES; do
    aws sagemaker delete-endpoint-config --endpoint-config-name "$EPC" --region "$REGION" >/dev/null 2>&1 && \
        echo "  OK エンドポイント設定削除: $EPC" || true
done
echo ""

# =============================================================================
# M06: Model Monitor スケジュール
# =============================================================================
echo "----------------------------------------------"
echo " [M06] Monitoring Schedule の削除"
echo "----------------------------------------------"
MS_NAMES=$(aws sagemaker list-monitoring-schedules --region "$REGION" \
    --query "MonitoringScheduleSummaries[?starts_with(MonitoringScheduleName, '$PREFIX')].MonitoringScheduleName" \
    --output text 2>/dev/null || echo "")
for MS in $MS_NAMES; do
    aws sagemaker delete-monitoring-schedule --monitoring-schedule-name "$MS" --region "$REGION" >/dev/null 2>&1 && \
        echo "  OK モニタリングスケジュール削除: $MS" || echo "  WARN 削除失敗: $MS"
done
[ -z "$MS_NAMES" ] && echo "  -- モニタリングスケジュールなし（スキップ）"
echo ""

# =============================================================================
# モデル（M02 / M04 / M05）
# =============================================================================
echo "----------------------------------------------"
echo " [M02/M04/M05] SageMaker モデルの削除"
echo "----------------------------------------------"
MODEL_NAMES=$(aws sagemaker list-models --region "$REGION" \
    --query "Models[?starts_with(ModelName, '$PREFIX')].ModelName" \
    --output text 2>/dev/null || echo "")
for M in $MODEL_NAMES; do
    aws sagemaker delete-model --model-name "$M" --region "$REGION" >/dev/null 2>&1 && \
        echo "  OK モデル削除: $M" || true
done
[ -z "$MODEL_NAMES" ] && echo "  -- モデルなし（スキップ）"
echo ""

# =============================================================================
# M04: SageMaker Pipeline
# =============================================================================
echo "----------------------------------------------"
echo " [M04] SageMaker Pipeline の削除"
echo "----------------------------------------------"
PIPE_NAMES=$(aws sagemaker list-pipelines --region "$REGION" \
    --query "PipelineSummaries[?starts_with(PipelineName, '$PREFIX')].PipelineName" \
    --output text 2>/dev/null || echo "")
for P in $PIPE_NAMES; do
    aws sagemaker delete-pipeline --pipeline-name "$P" --region "$REGION" >/dev/null 2>&1 && \
        echo "  OK パイプライン削除: $P" || echo "  WARN パイプライン削除失敗: $P"
done
[ -z "$PIPE_NAMES" ] && echo "  -- パイプラインなし（スキップ）"
echo ""

# =============================================================================
# M03: Model Registry（Model Package Group とバージョン）
# =============================================================================
echo "----------------------------------------------"
echo " [M03] Model Package Group の削除"
echo "----------------------------------------------"
MPG_NAMES=$(aws sagemaker list-model-package-groups --region "$REGION" \
    --query "ModelPackageGroupSummaryList[?starts_with(ModelPackageGroupName, '$PREFIX')].ModelPackageGroupName" \
    --output text 2>/dev/null || echo "")
for MPG in $MPG_NAMES; do
    # 先に配下のモデルパッケージ（バージョン）を削除する必要がある
    PKG_ARNS=$(aws sagemaker list-model-packages --model-package-group-name "$MPG" --region "$REGION" \
        --query "ModelPackageSummaryList[].ModelPackageArn" --output text 2>/dev/null || echo "")
    for ARN in $PKG_ARNS; do
        aws sagemaker delete-model-package --model-package-name "$ARN" --region "$REGION" >/dev/null 2>&1 && \
            echo "  OK モデルパッケージ削除: $ARN" || true
    done
    aws sagemaker delete-model-package-group --model-package-group-name "$MPG" --region "$REGION" >/dev/null 2>&1 && \
        echo "  OK モデルグループ削除: $MPG" || echo "  WARN モデルグループ削除失敗: $MPG"
done
[ -z "$MPG_NAMES" ] && echo "  -- モデルグループなし（スキップ）"
echo ""

# =============================================================================
# M03: Feature Store（Feature Group）
# =============================================================================
echo "----------------------------------------------"
echo " [M03] Feature Group の削除"
echo "----------------------------------------------"
FG_NAMES=$(aws sagemaker list-feature-groups --region "$REGION" \
    --query "FeatureGroupSummaries[?starts_with(FeatureGroupName, '$PREFIX')].FeatureGroupName" \
    --output text 2>/dev/null || echo "")
for FG in $FG_NAMES; do
    aws sagemaker delete-feature-group --feature-group-name "$FG" --region "$REGION" >/dev/null 2>&1 && \
        echo "  OK Feature Group 削除: $FG" || echo "  WARN Feature Group 削除失敗: $FG"
done
[ -z "$FG_NAMES" ] && echo "  -- Feature Group なし（スキップ）"
echo ""

# =============================================================================
# M05: Application Auto Scaling のスケーラブルターゲット
# =============================================================================
echo "----------------------------------------------"
echo " [M05] オートスケーリングターゲットの登録解除"
echo "----------------------------------------------"
ST_IDS=$(aws application-autoscaling describe-scalable-targets \
    --service-namespace sagemaker --region "$REGION" \
    --query "ScalableTargets[?starts_with(ResourceId, 'endpoint/$PREFIX')].ResourceId" \
    --output text 2>/dev/null || echo "")
for RID in $ST_IDS; do
    aws application-autoscaling deregister-scalable-target \
        --service-namespace sagemaker \
        --resource-id "$RID" \
        --scalable-dimension sagemaker:variant:DesiredInstanceCount \
        --region "$REGION" >/dev/null 2>&1 && \
        echo "  OK スケーラブルターゲット解除: $RID" || true
done
[ -z "$ST_IDS" ] && echo "  -- スケーラブルターゲットなし（スキップ）"
echo ""

echo "=============================================="
echo " クリーンアップ完了!"
echo "=============================================="
echo ""
echo "  以下は手動確認を推奨します:"
echo "  - S3: mlops-handson プレフィックスのデータ・アーティファクト"
echo "  - Feature Store のオフラインストア（S3）"
echo "  - CloudWatch アラーム（オートスケーリングが作成したもの）"
