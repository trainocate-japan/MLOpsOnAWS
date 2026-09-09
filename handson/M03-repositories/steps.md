# モジュール 3: Repeatable MLOps - リポジトリ - ハンズオン手順

## パート 1: データのバージョン管理（15分）

### ステップ 1.1: プロジェクトの準備

```bash
cd ~/handson/M03-repositories
```

### ステップ 1.2: S3 バージョニングでデータを管理

```bash
python data_versioning_demo.py
```

- S3 バージョニングを有効化し、同じキーに複数バージョンが保持されることを確認
- データバージョニングが**再現性**と**データドリフト検知**（M06）の基盤になることを押さえる

**議論（スライド対応）**: データバージョニングの価値は？（再現性・変換の追跡・ベースライン）

---

## パート 2: Feature Store で特徴量を管理（20分）

### ステップ 2.1: 特徴量グループを作成して取り込む

```bash
python feature_store_demo.py
```

- **record identifier**（`abalone_id`）と **event time**（`event_time`）の役割を確認
- オンラインストア（低レイテンシー）とオフラインストア（S3 の履歴）の違いを押さえる
- 取り込んだ特徴量をオンラインストアから取得できることを確認

**共有フィーチャーストアの価値（スライド対応）**: 反復可能性・検索性と再利用性・信頼できる唯一の情報源

**議論（スライド対応・ナレッジチェック 2）**:
SageMaker Feature Store は組み込みアルゴリズムのトレーニングに使える機能を提供する（正）

---

## パート 3: Model Registry でモデルを管理（20分）

### ステップ 3.1: モデルを登録・バージョン管理・承認

```bash
python model_registry_demo.py
```

このスクリプトは以下を実行します。

1. **Model Package Group** を作成（モデルのカタログ。バージョンをまとめる単位）
2. M02 のモデルアーティファクトを**モデルバージョンとして登録**（`PendingManualApproval`）
3. 承認ステータスを **`Approved`** に更新
4. バージョン一覧を表示

**モデルレジストリがカタログ化する情報（スライド対応）**:

| 項目 | 例 |
|------|-----|
| トレーニングに使用したデータ | S3 パス |
| ハイパーパラメータ | num_round, max_depth, eta |
| アルゴリズムとフレームワーク | XGBoost 1.7-1 |
| コンテナイメージ | ECR の image URI |
| 承認ステータス | Pending → Approved |

### ステップ 3.2: セキュリティに関する考慮事項（スライド対応）

- リソースに**タグ**を適用（モデルグループ・プロジェクト・チームの識別）→ スクリプトで `project` / `team` タグを付与済み
- タグベースのアクセス制御・管理ポリシー

---

## パート 4: コードリポジトリのベストプラクティス（5分）

スクリプト実行は不要です。以下を確認します（スライド対応）。

- **README** にリポジトリ概要・前提条件・インストール手順を記載
- **ブランチ戦略**（誰がどのブランチにコミットできるか）
- **プルリクエスト**でコードレビュー（認証情報・セキュリティの確認）
- **AWS CloudTrail** で API・ユーザーアクティビティをロギング

---

## ナレッジチェック（スライド対応）

1. Repeatable フェーズの主な焦点は？ → **B: 自動化に重点を置き、データ・コード・モデルリポジトリを標準化してデプロイ時間を短縮**
2. モデルレジストリの役割は？（2 つ）→ **バージョン管理・コラボレーション・ガバナンスを提供 / メタデータの関連付け**
3. コードリポジトリのセキュリティのベストプラクティスは？ → **アクセス制御・プルリクエスト・ロギング**

---

## 参考ドキュメント

- [Create a Model Group (Model Registry)](https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry-model-group.html)
- [Register a Model Version](https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry-version.html)
- [Update the Approval Status of a Model](https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry-approve.html)
- [Amazon SageMaker Feature Store](https://docs.aws.amazon.com/sagemaker/latest/dg/feature-store.html)
- [Using versioning in S3 buckets](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)
