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

**議論**: データバージョニングの価値は？（再現性・変換の追跡・ベースライン）

---

## パート 2: Feature Store で特徴量を管理（20分）

### ステップ 2.1: 特徴量グループを作成して取り込む

```bash
python feature_store_demo.py
```

- **record identifier**（`abalone_id`）と **event time**（`event_time`）の役割を確認
- オンラインストア（低レイテンシー）とオフラインストア（S3 の履歴）の違いを押さえる
- 取り込んだ特徴量をオンラインストアから取得できることを確認

**Feature Store の全体像**（講義スライド「トレーニングと推論に SageMaker Feature Store を使う」）:

```
データソース                SageMaker Feature Store         利用先
（ストリーミング/バッチ）                                    
        │   特徴量エンジニアリング   ┌─ オンラインストア ─┐   → リアルタイム推論
        └──────────────────────────►│   ↕ 自動同期        │   → バッチ推論
                                     └─ オフラインストア ─┘   → トレーニングジョブ
                                        （S3 の履歴）
```

- **オンラインストア**: 低レイテンシーで最新の特徴量を取得（リアルタイム推論向け）→ 今回 `get_record` で確認
- **オフラインストア**: S3 に履歴を蓄積（トレーニング・バッチ向け）→ ステップ 2.2 で確認
- 両者は**自動同期**され、学習と推論で**一貫した特徴量**を使えるのがポイント

> **同期の向きに注意**: スライドの「自動同期」の矢印は上下両方向に描かれていますが、これは両ストアが同じ特徴量を整合の取れた状態で保持していることを表す概念図です。実際のデータ複製は書き込み（`PutRecord` / `ingest`）を起点に **オンラインストア → オフラインストア** の一方向で、オフラインから逆流はしません。そのため、オフラインの S3 に直接ファイルを置いてもオンラインには反映されません。オンラインにも反映したい場合は必ず `PutRecord` / `ingest` を使います。
>
> この一方向性と非同期性が、前述の「学習・推論スキュー（train/serving skew）」を生む余地になります。だから両ストアを有効化して Feature Store に同期を任せ、正規の書き込み経路を通すことが重要です。

**共有フィーチャーストアの価値**: 反復可能性・検索性と再利用性・信頼できる唯一の情報源

> SageMaker Feature Store の特徴量は、そのまま組み込みアルゴリズムのトレーニングにも利用できます。

### ステップ 2.2: オフラインストア（S3 の履歴）を確認する

> **進め方（待ち時間を吸収する）**: オフラインストアへの書き込みは**非同期**で、S3 に反映されるまで数分かかります。そこで次の順序で進めます。
>
> 1. ステップ 2.1（`feature_store_demo.py`）を実行し、出力されたオフラインストアの S3 パスを控える
> 2. 反映を待つ間に**パート3（Model Registry）へ進む**
> 3. パート3が終わったら**このステップ 2.2 に戻り**、S3 を確認する
>
> こうすると、オンラインストア（即時に取得できる）とオフラインストア（履歴が S3 に溜まるまで時間がかかる）の**性質の違い**も体感できます。

`feature_store_demo.py` は `create()` 時に S3 URI を指定しているため、オンラインストアだけでなく**オフラインストアも自動で作成**されます。スクリプト末尾に表示されるオフラインストアの S3 パスを確認します。

パート3から戻ってきたら、スクリプトが出力した URI を使って中身を確認します（この頃には反映されているはずです）。

```bash
# スクリプトが出力した ResolvedOutputS3Uri を使う
aws s3 ls --recursive s3://<出力された offline-store のパス>/
```

- 反映後、`.../data/year=.../month=.../day=.../hour=.../*.parquet` というパーティション構造で履歴が保存されていることを確認
- オンラインストア（`get_record` による低レイテンシー取得）とオフラインストア（S3 上の履歴データ。学習・バッチ処理向け）の**用途の違い**を押さえる

> オフラインストアはドリフト検知（M06）やモデルの再学習で使う**時系列の履歴**を蓄積します。書き込みが非同期のため、取り込み直後は空に見えることがあります。

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

**モデルレジストリがカタログ化する情報**:

| 項目 | 例 |
|------|-----|
| トレーニングに使用したデータ | S3 パス |
| ハイパーパラメータ | num_round, max_depth, eta |
| アルゴリズムとフレームワーク | XGBoost 1.7-1 |
| コンテナイメージ | ECR の image URI |
| 承認ステータス | Pending → Approved |

### ステップ 3.2: セキュリティに関する考慮事項

- リソースに**タグ**を適用（モデルグループ・プロジェクト・チームの識別）→ スクリプトで `project` / `team` タグを付与済み
- タグベースのアクセス制御・管理ポリシー

> **ここでステップ 2.2 に戻る**: パート2で控えたオフラインストアの S3 パスを `aws s3 ls --recursive` で確認します。この頃には特徴量が Parquet として反映されているはずです。

---

## パート 4: コードリポジトリのベストプラクティス（5分）

スクリプト実行は不要です。以下を確認します。

- **README** にリポジトリ概要・前提条件・インストール手順を記載
- **ブランチ戦略**（誰がどのブランチにコミットできるか）
- **プルリクエスト**でコードレビュー（認証情報・セキュリティの確認）
- **AWS CloudTrail** で API・ユーザーアクティビティをロギング

---

## 参考ドキュメント

- [Create a Model Group (Model Registry)](https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry-model-group.html)
- [Register a Model Version](https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry-version.html)
- [Update the Approval Status of a Model](https://docs.aws.amazon.com/sagemaker/latest/dg/model-registry-approve.html)
- [Amazon SageMaker Feature Store](https://docs.aws.amazon.com/sagemaker/latest/dg/feature-store.html)
- [Using versioning in S3 buckets](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html)
