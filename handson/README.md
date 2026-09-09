# MLOps Engineering on AWS - ハンズオンガイド

## コース概要

このハンズオンガイドは「MLOps Engineering on AWS（日本語）」研修コースの
各モジュール（モジュール 1 〜 モジュール 6）に対応した、実践的なシナリオと手順を提供します。
スライドで学んだ MLOps の概念（Initial → Repeatable → Reliable → Scalable の成熟度モデル）を、
Amazon SageMaker AI を使って実際に手を動かして確認することで理解を深めることを目的としています。

各モジュールのフォルダには次の 3 種類のファイルがあります。

- `scenario.md` … 業務シナリオ・学習目標・アーキテクチャ・所要時間
- `steps.md` … コンソール操作とスクリプト実行を含むハンズオン手順
- `*.py` … デモ用の Python スクリプト（boto3 / SageMaker SDK を使用します）

すべてのモジュールは、研修のラボストーリー **AnyCompany Consulting のアワビ (Abalone) の年齢予測**
（物理的な測定値から年齢を回帰予測する XGBoost モデル）を題材に一貫して構成されています。

## モジュール一覧

| モジュール | テーマ | フォルダ | 目安時間 |
|-----------|--------|---------|---------|
| M01 | MLOps の導入（ライフサイクル・成熟度モデル・DevOps との比較・ガバナンス） | `M01-intro-mlops` | 40分 |
| M02 | Initial MLOps: SageMaker Studio の実験環境（組み込みアルゴリズム・BYOS/BYOC/BYOM） | `M02-experimentation-studio` | 60分 |
| M03 | Repeatable MLOps: リポジトリ（データバージョニング・Feature Store・Model Registry） | `M03-repositories` | 60分 |
| M04 | Repeatable MLOps: オーケストレーション（SageMaker Pipelines・推論オプション） | `M04-orchestration` | 60分 |
| M05 | Reliable MLOps: スケーリングとテスト（オートスケーリング・A/B/シャドー・ブルーグリーン） | `M05-scaling-testing` | 60分 |
| M06 | Reliable MLOps: モニタリング（Model Monitor・データドリフト・リネージ・再学習） | `M06-monitoring` | 60分 |

## 前提条件

### 環境要件

- AWS アカウント（管理者アクセス）
- AWS CLI v2 設定済み
- Python 3.12+（EC2 デモ環境では venv が自動で有効化されます）
- `infra/` の CloudFormation スタックをデプロイ済み（SageMaker 実行ロールを含む）

### SageMaker 実行ロール

トレーニングジョブやエンドポイントには **SageMaker 実行ロール** が必要です。
本ハンズオンのスクリプトは、次の優先順位でロール ARN を解決します。

1. 環境変数 `SAGEMAKER_ROLE_ARN`（EC2 デモ環境で自動設定）
2. `sagemaker.get_execution_role()`（SageMaker Studio 内で実行する場合）

EC2 デモ環境以外で実行する場合は、事前に環境変数を設定してください。

```bash
export SAGEMAKER_ROLE_ARN=arn:aws:iam::<ACCOUNT_ID>:role/MLOpsHandsonSageMakerRole
```

### 使用するインスタンスタイプ（コスト最適化のため小さめを使用）

| 用途 | インスタンスタイプ |
|------|------------------|
| トレーニング（XGBoost） | `ml.m5.large` |
| リアルタイムエンドポイント | `ml.m5.large` |
| 処理ジョブ（前処理・評価） | `ml.m5.large` |

> 実行前に `aws sts get-caller-identity` で正しいアカウントか確認してください。
> リージョンは `us-east-1`（バージニア北部）を推奨します。

### Python パッケージ

EC2 デモ環境には以下がプリインストールされています（`infra/demo-ec2.yaml` 参照）。

- `boto3`
- `sagemaker`（SageMaker Python SDK v2）
- `pandas`, `numpy`, `scikit-learn`

ローカルで実行する場合は以下でインストールできます。

```bash
pip install boto3 "sagemaker>=2.200,<3" pandas numpy scikit-learn
```

## フォルダ構造

```
handson/
├── README.md                        # このファイル
├── cleanup_all.sh                   # 全リソース一括削除スクリプト
├── common.py                        # 共通ユーティリティ（ロール解決・リージョン・命名）
├── M01-intro-mlops/
│   ├── scenario.md
│   ├── steps.md
│   ├── ml_lifecycle_explorer.py     # ML ライフサイクルと成熟度モデルの確認
│   └── devops_vs_mlops.py           # DevOps と MLOps の比較
├── M02-experimentation-studio/
│   ├── scenario.md
│   ├── steps.md
│   ├── prepare_abalone_data.py      # アワビデータの取得・前処理・S3 アップロード
│   ├── train_builtin_xgboost.py     # 組み込み XGBoost でトレーニング（アルゴリズムモード）
│   ├── train_script_mode.py         # スクリプトモード (BYOS) でのトレーニング
│   ├── abalone_train.py             # BYOS 用のトレーニングスクリプト
│   └── list_sagemaker_domains.py    # SageMaker Domain の確認
├── M03-repositories/
│   ├── scenario.md
│   ├── steps.md
│   ├── feature_store_demo.py        # SageMaker Feature Store（特徴量のバージョン管理）
│   ├── model_registry_demo.py       # Model Registry（登録・バージョン・承認）
│   └── data_versioning_demo.py      # S3 バージョニングによるデータ管理
├── M04-orchestration/
│   ├── scenario.md
│   ├── steps.md
│   ├── build_pipeline.py            # SageMaker Pipelines（処理→学習→評価→条件→登録）
│   ├── evaluate.py                  # パイプラインの評価ステップ用スクリプト
│   ├── deploy_realtime_endpoint.py  # リアルタイムエンドポイントのデプロイ
│   └── inference_options.py         # 推論オプション（リアルタイム/サーバーレス/非同期/バッチ）の比較
├── M05-scaling-testing/
│   ├── scenario.md
│   ├── steps.md
│   ├── autoscaling_demo.py          # ターゲット追跡オートスケーリングの設定
│   ├── ab_test_variants.py          # 本番バリアントによる A/B テスト
│   ├── shadow_test.py               # シャドーバリアントテスト
│   └── blue_green_deploy.py         # ブルー/グリーン（Canary/Linear）デプロイ
└── M06-monitoring/
    ├── scenario.md
    ├── steps.md
    ├── enable_data_capture.py       # データキャプチャ付きエンドポイントのデプロイ
    ├── model_monitor_baseline.py    # Model Monitor のベースライン作成とスケジュール
    ├── generate_drift_traffic.py    # データドリフトを発生させるトラフィック生成
    └── lineage_tracking_demo.py     # Lineage Tracking によるトラブルシューティング
```

## 使い方

1. 各モジュールフォルダ内の `scenario.md` でシナリオと学習目標を確認します。
2. `steps.md` の手順に従ってハンズオンを実施します。
3. Python スクリプトを順番に実行してデモ動作を確認します。
4. 終了後は下記クリーンアップ手順に従ってリソースを削除します。

> **推奨実行順序**: M02 → M03 → M04 → M05 → M06。
> M02 で作成したモデルアーティファクトを後続モジュールで再利用します。

## クリーンアップ

多くのモジュールが AWS リソース（エンドポイント、モデル、Feature Group、Model Package Group、
Pipeline、Monitoring Schedule など）を作成します。研修終了後は以下で一括削除できます。

```bash
cd ~/handson
bash cleanup_all.sh
```

### 対象リソース一覧

| モジュール | 削除対象 |
|-----------|---------|
| M02 | トレーニングで作成したモデル、S3 のデータ・アーティファクト |
| M03 | Feature Group、Model Package Group（モデルバージョン） |
| M04 | SageMaker Pipeline、リアルタイムエンドポイント、モデル、エンドポイント設定 |
| M05 | A/B・シャドーエンドポイント、オートスケーリングターゲット |
| M06 | Monitoring Schedule、データキャプチャ付きエンドポイント |

> スクリプトは冪等です（リソースが存在しなければスキップします）。
> 実行前に `aws sts get-caller-identity` で正しいアカウントか確認してください。

## コスト管理

- 各ハンズオンの推定コスト: $2〜$10
- **リアルタイムエンドポイントは起動中ずっと課金されます。** 各モジュール完了後に必ず削除してください。
- Model Monitor のスケジュールジョブ（M06）も定期的にインスタンスを起動するため、使用後は必ず削除してください。

## トラブルシューティング

### ロールが見つからない

```
ValueError: SAGEMAKER_ROLE_ARN が設定されていません
```

→ `export SAGEMAKER_ROLE_ARN=arn:aws:iam::<ACCOUNT_ID>:role/MLOpsHandsonSageMakerRole` を実行してください。
EC2 デモ環境では自動設定されています。

### ResourceLimitExceeded（インスタンス上限）

```
ResourceLimitExceeded: The account-level service limit 'ml.m5.large for ... ' is 0 Instances
```

→ SageMaker のインスタンスタイプごとにクォータ引き上げが必要な場合があります。
Service Quotas コンソールから該当インスタンスタイプの上限緩和を申請してください。

### エンドポイントの作成に時間がかかる

→ リアルタイムエンドポイントの `InService` までには数分かかります。
`aws sagemaker describe-endpoint --endpoint-name <name>` でステータスを確認できます。

### AccessDenied（PassRole）

→ EC2 のインスタンスロールが SageMaker 実行ロールを `iam:PassRole` できる必要があります。
`infra/demo-ec2.yaml` の `PassSageMakerRole` ポリシーで許可済みです。
