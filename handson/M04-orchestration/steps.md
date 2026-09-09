# モジュール 4: Repeatable MLOps - オーケストレーション - ハンズオン手順

## パート 1: モデル構築パイプライン（25分）

### ステップ 1.1: プロジェクトの準備

```bash
cd ~/handson/M04-orchestration
```

### ステップ 1.2: パイプラインを作成して実行

```bash
python build_pipeline.py
```

このパイプラインは以下のステップをつなぎます。

```
AbaloneTrain（学習）→ AbaloneEval（評価）→ AbaloneRmseCheck（条件）→ AbaloneRegister（登録）
```

- **TrainingStep**: 組み込み XGBoost で学習
- **ProcessingStep**: `evaluate.py` でテストデータの RMSE を計算し `evaluation.json` に出力
- **ConditionStep**: RMSE がしきい値（既定 3.0）以下なら登録ステップを実行
- **RegisterModel**: Model Registry に登録

> 実行に 10〜15 分かかります。作成のみで実行しない場合は `python build_pipeline.py --no-run`。

### ステップ 1.3: パイプラインパラメータを確認

`TrainingInstanceType` と `RmseThreshold` はパイプラインパラメータです。
実行のたびに値を変えられるため、**反復可能性**が確保されます。
これにより、しきい値を満たすモデルだけを条件ステップ経由で登録できます。

### ステップ 1.4: ベストプラクティスの確認

- パイプラインパラメーター / プロパティファイルと JsonGet / キャッシュ / 再試行ポリシー / 選択的実行

---

## パート 2: リアルタイム推論エンドポイント（20分）

### ステップ 2.1: モデルをデプロイして推論

```bash
python deploy_realtime_endpoint.py
```

- **Model → EndpointConfig → Endpoint** の 3 段階で SageMaker がインフラを管理
- デプロイ後、アワビの測定値から輪紋数（年齢の指標）を予測できることを確認

**議論**: モデルの登録後、エンドポイントを作成する前に何の手順が必要ですか？（承認・モデル作成・エンドポイント設定）

### ステップ 2.2: エンドポイントを削除（重要）

```bash
python deploy_realtime_endpoint.py --delete
```

> リアルタイムエンドポイントは**起動中ずっと課金**されます。確認後は必ず削除してください。

---

## パート 3: 推論オプションの比較（10分）

デプロイしたリアルタイムエンドポイントを踏まえ、ユースケースに応じた推論オプションを比較します。
以下は選択の指針です（M05 でリアルタイムエンドポイントのスケーリングとテストを扱います）。

| オプション | 向いているケース |
|-----------|----------------|
| リアルタイム | 低レイテンシーの同期推論（常時稼働） |
| サーバーレス | 断続的なトラフィック・コールドスタート許容 |
| 非同期 | 処理時間が長い・大きなペイロード・キューイング |
| バッチ変換 | 大規模データセット全体のオフライン推論 |

エンドツーエンドのオーケストレーションでは、以下の選択肢があります。

| ツール | 特徴 |
|--------|------|
| SageMaker AI Pipelines | ML に特化・パイプラインパラメータ・キャッシュ |
| AWS Step Functions | サーバーレスの汎用ワークフロー・ヒューマンインザループ |
| Amazon MWAA (Airflow) | 既存の Airflow 資産を活用 |
| SageMaker Projects | CI/CD テンプレートを含むプロジェクト単位の管理 |

---

## 参考ドキュメント

- [Amazon SageMaker Pipelines](https://docs.aws.amazon.com/sagemaker/latest/dg/pipelines.html)
- [Define a Pipeline](https://docs.aws.amazon.com/sagemaker/latest/dg/define-pipeline.html)
- [Deploy models for real-time inference](https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints.html)
- [Serverless Inference](https://docs.aws.amazon.com/sagemaker/latest/dg/serverless-endpoints.html)
- [Asynchronous inference](https://docs.aws.amazon.com/sagemaker/latest/dg/async-inference.html)
- [Batch Transform](https://docs.aws.amazon.com/sagemaker/latest/dg/batch-transform.html)
