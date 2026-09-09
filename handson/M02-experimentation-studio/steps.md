# モジュール 2: Initial MLOps - SageMaker Studio の実験環境 - ハンズオン手順

## パート 1: 実験環境の確認（10分）

### ステップ 1.1: プロジェクトの準備

```bash
cd ~/handson/M02-experimentation-studio
echo $SAGEMAKER_ROLE_ARN   # ロール ARN が表示されることを確認
```

### ステップ 1.2: SageMaker Domain を確認

```bash
python list_sagemaker_domains.py
```

- SageMaker Studio の実験環境が **Domain / ユーザープロファイル / スペース** で構成されることを確認
- 標準化された環境（ライフサイクル構成・Role Manager・Service Catalog）の役割を押さえる

---

## パート 2: アワビデータの準備（10分）

### ステップ 2.1: データを取得・前処理して S3 にアップロード

```bash
python prepare_abalone_data.py
```

- アワビの測定値（性別・長さ・直径・重量など）から輪紋数 (rings) を予測する**回帰**問題
- 組み込み XGBoost の要件（**1 列目が目的変数・ヘッダーなし CSV**）に合わせて前処理
- train / validation / test に分割して S3 に配置されることを確認

---

## パート 3: 組み込みアルゴリズムでのトレーニング（15分）

### ステップ 3.1: 組み込み XGBoost で学習

```bash
python train_builtin_xgboost.py
```

- `image_uris.retrieve` で **AWS 管理の XGBoost コンテナイメージ**を取得
- SageMaker がトレーニング用に **Docker コンテナを自動起動**することを確認
- 学習後、S3 に **`model.tar.gz`（モデルアーティファクト）** が出力されることを確認
- 出力されたモデルアーティファクトの S3 パスをメモ（後続モジュールで使用）

**議論**: コンテナを使うメリットは何ですか？（再現性・移植性・依存関係の分離）

---

## パート 4: スクリプトモード (BYOS) でのトレーニング（15分）

### ステップ 4.1: 独自スクリプトを持ち込んで学習

```bash
python train_script_mode.py
```

- `entry_point=abalone_train.py` で**自分の学習ロジック**を持ち込む
- コンテナイメージは AWS 管理のまま、学習コードだけを差し替えられる
- `abalone_train.py` が SageMaker 標準の環境変数（`SM_MODEL_DIR` / `SM_CHANNEL_TRAIN`）を使う点を確認

### ステップ 4.2: BYOS スクリプトの構造を確認

```bash
cat abalone_train.py
```

| 環境変数 | 役割 |
|---------|------|
| `SM_CHANNEL_TRAIN` | 学習データのローカルパス（コンテナ内） |
| `SM_CHANNEL_VALIDATION` | 検証データのローカルパス |
| `SM_MODEL_DIR` | ここに保存したものが `model.tar.gz` になる |

---

## パート 5: コンテナアプローチの使い分けとまとめ（5分）

### コンテナアプローチの選択

| アプローチ | 使うべきケース |
|-----------|--------------|
| 組み込みアルゴリズム | 標準的な問題（今回の XGBoost 回帰） |
| BYOS（独自スクリプト） | フレームワークは標準だが学習ロジックが独自 |
| BYOC（独自コンテナ） | 独自フレームワーク・特殊な依存関係（ECR にイメージを登録） |
| BYOM（独自モデル） | 学習済みモデルを持ち込む |

> BYOC では `sm-docker build .`（SageMaker Studio Image Build CLI）で
> Docker イメージをビルドし、Amazon ECR にプッシュします。

---

## 参考ドキュメント

- [How to use SageMaker AI XGBoost](https://docs.aws.amazon.com/sagemaker/latest/dg/xgboost-how-to-use.html)
- [Use Your Own Training Algorithms (BYOC)](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo.html)
- [Amazon SageMaker Studio](https://docs.aws.amazon.com/sagemaker/latest/dg/studio.html)
- [Use the SageMaker Studio Image Build CLI](https://docs.aws.amazon.com/sagemaker/latest/dg/studio-byoi.html)
