# モジュール 3: Repeatable MLOps - リポジトリ - ハンズオンシナリオ

## シナリオ概要

アワビ年齢予測モデルの実験は成功しましたが、AnyCompany Consulting のチームは
「**同じ特徴量を毎回作り直している**」「**どのモデルがどのデータで学習されたか分からない**」という
課題を抱えています。あなたは MLOps エンジニアとして、Repeatable フェーズに進むために
**データ・モデル・コードのバージョン管理**の仕組みを導入します。

このモジュールでは、SageMaker Feature Store で特徴量を共有・再利用可能にし、
SageMaker Model Registry でモデルをカタログ化・バージョン管理・承認します。

## 学習目標

このハンズオンを完了すると、以下ができるようになります。

1. **データバージョニングの価値を説明する**: 再現性・データドリフト検知の基盤としての重要性
2. **Feature Store を使う**: 特徴量グループを作成し、特徴量を取り込む（信頼できる唯一の情報源）
3. **Model Registry を使う**: Model Package Group を作りモデルバージョンを登録する
4. **モデルの承認ステータスを管理する**: PendingManualApproval → Approved の遷移を体験する
5. **セキュリティのベストプラクティスを説明する**: タグによる識別・アクセス制御・ロギング

## Repeatable フェーズの構成要素（スライド対応）

| 要素 | 内容 |
|------|------|
| バージョン管理 | コード・モデル・データをバージョン管理し、コミットのたびに追跡 |
| オーケストレーション | 手作業を減らし、一貫性のある反復可能なワークフローを作る（M04 で扱う） |

## リポジトリオプション（スライド対応）

| 対象 | AWS サービス |
|------|------------|
| データ / 特徴量 | Amazon S3（バージョニング）、SageMaker Feature Store |
| モデル | Amazon S3、Amazon ECR、SageMaker Model Registry |
| コード | Git リポジトリ（AWS CodeCommit・サードパーティ） |

## 使用する AWS サービス

- Amazon SageMaker Feature Store（オンライン/オフラインストア）
- Amazon SageMaker Model Registry（Model Package Group）
- Amazon S3（データバージョニング）

## 所要時間

約 60 分

## 前提条件

- M02 を完了し、モデルアーティファクト（`model.tar.gz`）が S3 にあること
- `SAGEMAKER_ROLE_ARN` が設定されていること
