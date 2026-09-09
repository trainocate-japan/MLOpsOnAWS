# モジュール 1: MLOps の導入 - ハンズオン手順

このモジュールでは AWS リソースを作成しません。概念を整理するためのスクリプトを実行します。

## パート 1: ML ライフサイクルと成熟度モデルの整理（15分）

### ステップ 1.1: プロジェクトの準備

```bash
cd ~/handson/M01-intro-mlops
```

### ステップ 1.2: ML ライフサイクルと成熟度モデルを確認

```bash
python ml_lifecycle_explorer.py
```

出力を見ながら、以下を確認します。

- ML ライフサイクルは **ビジネス課題 → データ → 特徴量 → 学習 → 評価 → デプロイ → 監視** の反復であること
- MLOps 成熟度モデルは **Initial → Repeatable → Reliable → Scalable** の 4 段階であること
- 各レベルで「コラボレーション・データ処理・トレーニング・デプロイ」がどう進化するか

**議論**: あなたの組織（またはチーム）は今どのレベルにいますか？次に上げるべきレベルは？

---

## パート 2: DevOps と MLOps の比較（15分）

### ステップ 2.1: 比較スクリプトを実行

```bash
python devops_vs_mlops.py
```

- DevOps は主に**コード**を扱い、MLOps は**コード + データ + モデル**を扱う点を確認
- 「プログラマーがコードを書き、データがモデルを書く」という考え方を押さえる
- MLOps 特有の性質（一貫性・再現性・監査可能性・説明可能性など）を確認
- MLOps に関わるロール（DevOps / データ / データサイエンス / MLOps / 承認者 / ガバナンス）を確認

**議論**: 組織が DevOps から MLOps に移行するとき、チームコラボレーションはどう進化すべきですか？

---

## パート 3: セキュリティとガバナンスの考察（10分）

### ステップ 3.1: MLSecOps と ML ガバナンス

スクリプト実行は不要です。以下の観点をチームで話し合います（スライド対応）。

**MLSecOps の 4 つの考慮事項**

| 領域 | 例 |
|------|-----|
| ネットワークのセキュリティ | VPC 内での学習・推論、エンドポイントの分離 |
| コードとコンテナのセキュリティ | イメージスキャン、依存関係の脆弱性チェック |
| モデルのセキュリティ | モデルの改ざん防止、アクセス制御 |
| データのセキュリティ | PII の保護、暗号化、Lake Formation による権限管理 |

**ML ガバナンスが必要な理由**

- 文書とプロセスの標準化
- ビジネス指標の取得
- 複数ペルソナの権限管理
- モデルの透明性・説明可能性・監査可能性・セキュリティの確保

**議論（スライド対応）**:
- 組織内の ML システムのガバナンスについてどう思いますか？
- ML ガバナンスを実装しない場合のコストはどのくらいでしょうか？

---

## ナレッジチェック（スライド対応）

1. MLOps を構成する 3 つの柱は？ → **プロセス・ピープル・テクノロジー**（+ セキュリティとガバナンス）
2. 「自動データパイプライン」と「自動モデルビルドパイプライン」が特徴の成熟度レベルは？ → **Repeatable**
3. DevOps と比べて MLOps が追加で扱う成果物は？ → **データとモデル**

---

## 参考ドキュメント

- [MLOps foundation roadmap for enterprises with Amazon SageMaker](https://aws.amazon.com/blogs/machine-learning/mlops-foundation-roadmap-for-enterprises-with-amazon-sagemaker/)
- [Machine Learning Lens - AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/machine-learning-lens.html)
- [MLOps - Amazon SageMaker AI](https://docs.aws.amazon.com/sagemaker/latest/dg/mlops.html)
