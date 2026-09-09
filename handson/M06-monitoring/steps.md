# モジュール 6: Reliable MLOps - モニタリング - ハンズオン手順

> 監視スケジュールと監視エンドポイントは課金対象です。**完了後は必ず削除**してください。

## パート 1: データキャプチャの有効化（15分）

### ステップ 1.1: プロジェクトの準備

```bash
cd ~/handson/M06-monitoring
```

### ステップ 1.2: データキャプチャ付きエンドポイントをデプロイ

```bash
python enable_data_capture.py
```

- **DataCaptureConfig** でエンドポイントの入力/出力を S3 にキャプチャ
- サンプリング率（`InitialSamplingPercentage`）でコストを調整できることを確認
- 通常トラフィックを送信し、キャプチャデータが S3 に保存されることを確認

**監視コスト削減のベストプラクティス（スライド対応）**: データキャプチャの有効/無効・リクエスト/応答の選択・サンプリングレート・インスタンスタイプ

---

## パート 2: ベースラインと監視スケジュール（20分）

### ステップ 2.1: ベースラインを作成して監視をスケジュール

```bash
python model_monitor_baseline.py
```

- 学習データから **statistics.json（統計）** と **constraints.json（制約）** を生成
- **1 時間ごと**の監視スケジュールを作成（キャプチャデータをベースラインと比較）
- CloudWatch メトリクスを有効化

### ステップ 2.2: ベースライン結果を確認

```bash
aws s3 ls s3://$(python -c "import sys,os;sys.path.append('..');from common import get_bucket;print(get_bucket())")/mlops-handson/monitor/baseline-results/ --recursive
```

---

## パート 3: データドリフトの検知（15分）

### ステップ 3.1: ドリフトを発生させる

```bash
python generate_drift_traffic.py
```

- ベースラインから大きく外れた入力（極端に大きいアワビ）を送信
- 次回の監視ジョブで**制約違反（データドリフト）**として検出される

### ステップ 3.2: 監視実行の確認

```bash
aws sagemaker list-monitoring-executions \
  --monitoring-schedule-name mlops-handson-abalone-dq-schedule \
  --region us-east-1
```

> 監視ジョブは 1 時間ごとに実行されます。直近の実行結果 (`ProcessingJobStatus` と違反) を確認します。

**ディスカッション（スライド対応）**: ML モデルを監視するとき、どんな運用上の課題が予想されますか？

---

## パート 4: トラブルシューティングと再学習（10分）

### ステップ 4.1: リネージで関連アーティファクトを追跡

```bash
python lineage_tracking_demo.py
```

- トレーニングジョブの**入力データ・イメージ・出力モデル**の関連を確認
- 「エラーのあるデータで学習したモデルのエンドポイントをロールバックする」ようなケースで、
  Lineage Tracking が関連の特定に役立つことを理解

### ステップ 4.2: 再学習アプローチの整理（スライド対応）

| アプローチ | 契機 |
|-----------|------|
| イベント駆動 | メトリクスのしきい値超過・状況の変化 |
| オンデマンド | 事業の変化に基づいて手動で |
| スケジュール | 指定された日時に定期的に |

**手動介入が必要になるケース（スライド対応）**: データ欠損 / 予想外のドリフト / 規制要件 / モデル用途の変更 / KPI 更新

**トラブルシューティングツール（スライド対応）**: Model Registry（バージョン）/ Model Cards（用途・リスク・評価）/ Lineage Tracking

---

## 全リソースの削除（重要）

```bash
python model_monitor_baseline.py --delete    # 監視スケジュール
python enable_data_capture.py --delete        # エンドポイント
# または
cd ~/handson && bash cleanup_all.sh
```

---

## ナレッジチェック（スライド対応）

1. Model Monitor でドリフトを検知する前提として必要なものは？ → **データキャプチャの有効化**
2. ベースラインが生成する 2 つのファイルは？ → **statistics.json と constraints.json**
3. メトリクスのしきい値超過で自動的に行う再学習アプローチは？ → **イベント駆動**

---

## 参考ドキュメント

- [Amazon SageMaker Model Monitor](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor.html)
- [Capture data](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-data-capture.html)
- [Create a Baseline](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-byoc-constraints.html)
- [Schedule monitoring jobs](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-scheduling.html)
- [Amazon SageMaker ML Lineage Tracking](https://docs.aws.amazon.com/sagemaker/latest/dg/lineage-tracking.html)
