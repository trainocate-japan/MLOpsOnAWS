# モジュール 6: Reliable MLOps - モニタリング - ハンズオン手順

> 監視エンドポイントは課金対象です。**完了後は必ず削除**してください。

> **重要（サービスの提供状況）**: Amazon SageMaker AI – Model Monitor は **2026-06-30 付でメンテナンスモード**に移行しました。
> **新規のお客様は監視スケジュール（データ品質ジョブ定義）を新規作成できません**（既存のお客様は影響を受けません）。
> 参照: [AWS サービスのメンテナンスモード](https://docs.aws.amazon.com/general/latest/gr/maintenance_services.html)
>
> 本ハンズオンは、この制約下でも学習が成立するよう次の方針で進めます。
> - **ベースライン生成**（statistics.json / constraints.json）までは実行して確認します。
> - **監視スケジュール作成**は試行し、メンテナンスモードで失敗した場合はスクリプトが自動で案内を表示して正常終了します（エラーで止まりません）。
> - スケジュールの代替として、**キャプチャデータを constraints.json と突き合わせて**ドリフトの考え方を学びます。

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

**監視コスト削減のベストプラクティス**: データキャプチャの有効/無効・リクエスト/応答の選択・サンプリングレート・インスタンスタイプ

---

## パート 2: ベースラインの作成（20分）

### ステップ 2.1: ベースラインを生成する

```bash
python model_monitor_baseline.py
```

- 学習データから **statistics.json（統計）** と **constraints.json（制約）** を生成します。
- 続けて監視スケジュール作成を**試行**します。
  - メンテナンスモードの環境では `ValidationException`（maintenance mode）となり、
    スクリプトが**代替案内を表示して正常終了**します（エラーで止まりません）。
  - スケジュールが作成された場合のみ、後片付けで `--delete` が必要になります。

### ステップ 2.2: ベースライン結果（constraints.json）を確認

```bash
BUCKET=$(python -c "import sys;sys.path.append('..');from common import get_bucket;print(get_bucket())")
aws s3 ls s3://$BUCKET/mlops-handson/monitor/baseline-results/ --recursive

# constraints.json を取得して中身を確認（各特徴量の期待レンジ・型など）
aws s3 cp s3://$BUCKET/mlops-handson/monitor/baseline-results/constraints.json - | head -40
```

- `constraints.json` に各特徴量の期待レンジ・型・欠損許容などの「制約」が入っていることを確認します。
- この制約が、次のパートで送るドリフトデータとの比較の基準になります。

---

## パート 3: データドリフトの確認（15分）

### ステップ 3.1: ドリフトした入力を送る

```bash
python generate_drift_traffic.py
```

- ベースラインから大きく外れた入力（極端に大きいアワビ）を送信します。
- 送信した入力はデータキャプチャ機能で S3 に保存されます。

### ステップ 3.2: キャプチャデータをベースラインと突き合わせる

```bash
BUCKET=$(python -c "import sys;sys.path.append('..');from common import get_bucket;print(get_bucket())")
aws s3 ls s3://$BUCKET/mlops-handson/monitor/datacapture/mlops-handson-abalone-monitored/ --recursive
```

- キャプチャされた入力の `length` などが、`constraints.json` の期待レンジを大きく外れていることを確認します。
  これが「データドリフトを検知する」という考え方の中核です。

> **メンテナンスモードでのドリフト検知の代替**: SageMaker の自動監視スケジュールが使えない場合でも、
> キャプチャデータ（S3）と `constraints.json` を比較する処理を自前のジョブ
> （SageMaker Processing / Lambda + EventBridge など）として実装し、逸脱を CloudWatch メトリクス・
> アラームに送れば、同等のドリフト監視を構成できます。

**ディスカッション**: ML モデルを監視するとき、どんな運用上の課題が予想されますか？（監視の粒度・しきい値の決め方・誤検知・コスト）

---

## パート 4: トラブルシューティングと再学習（10分）

### ステップ 4.1: リネージで関連アーティファクトを追跡

```bash
python lineage_tracking_demo.py
```

- トレーニングジョブの**入力データ・イメージ・出力モデル**の関連を確認
- 「エラーのあるデータで学習したモデルのエンドポイントをロールバックする」ようなケースで、
  Lineage Tracking が関連の特定に役立つことを理解

### ステップ 4.2: 再学習アプローチの整理

| アプローチ | 契機 |
|-----------|------|
| イベント駆動 | メトリクスのしきい値超過・状況の変化 |
| オンデマンド | 事業の変化に基づいて手動で |
| スケジュール | 指定された日時に定期的に |

**手動介入が必要になるケース**: データ欠損 / 予想外のドリフト / 規制要件 / モデル用途の変更 / KPI 更新

**トラブルシューティングツール**: Model Registry（バージョン）/ Model Cards（用途・リスク・評価）/ Lineage Tracking

---

## 全リソースの削除（重要）

```bash
python model_monitor_baseline.py --delete    # 監視スケジュール（作成された場合のみ。未作成ならスキップされます）
python enable_data_capture.py --delete        # エンドポイント（課金対象。必ず削除）
# または
cd ~/handson && bash cleanup_all.sh
```

> メンテナンスモードでスケジュールが作成されなかった場合、`--delete` は「見つからない（スキップ）」と表示されます。
> 課金の観点で最も重要なのは**エンドポイントの削除**です。

---

## 参考ドキュメント

- [AWS サービスのメンテナンスモード（Model Monitor を含む）](https://docs.aws.amazon.com/general/latest/gr/maintenance_services.html)
- [Amazon SageMaker Model Monitor](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor.html)
- [Capture data](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-data-capture.html)
- [Create a Baseline](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-byoc-constraints.html)
- [Schedule monitoring jobs](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-scheduling.html)
- [Amazon SageMaker ML Lineage Tracking](https://docs.aws.amazon.com/sagemaker/latest/dg/lineage-tracking.html)
