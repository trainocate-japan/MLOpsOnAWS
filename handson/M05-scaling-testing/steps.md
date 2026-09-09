# モジュール 5: Reliable MLOps - スケーリングとテスト - ハンズオン手順

> このモジュールは複数のエンドポイントを作成します。各パート完了後に `--delete` で削除するか、
> 最後に `cleanup_all.sh` を実行してください。**起動中のエンドポイントは課金されます。**

## パート 1: A/B テスト（本番バリアント）（15分）

### ステップ 1.1: プロジェクトの準備

```bash
cd ~/handson/M05-scaling-testing
```

### ステップ 1.2: 2 つのバリアントをデプロイして加重ルーティング

```bash
python ab_test_variants.py
```

- 1 つのエンドポイントに **VariantA / VariantB** を配置（各 50%）
- `InitialVariantWeight` によるトラフィック配分を確認
- `TargetVariant` で特定バリアントを直接呼び出せることを確認
- 応答ヘッダー `x-amzn-invoked-production-variant` でどちらが応答したか確認

**A/B テストとシャドーテストの違い（スライド対応）**: A/B は両モデルの実応答を比較。シャドーは応答を返さない。

---

## パート 2: シャドーテスト（15分）

### ステップ 2.1: シャドーバリアントをデプロイ

```bash
python shadow_test.py
```

- **ProductionVariants**（100% 応答）+ **ShadowProductionVariants**（複製を受信）の構成
- 本番へ呼び出すと、SageMaker が自動でシャドーにトラフィックを複製
- シャドーの応答はユーザーに返らない（**ユーザー影響ゼロ**で新モデルを評価）
- 制約: シャドー使用時は本番 1・シャドー 1 のみ。サーバーレス/非同期/MME/MCE とは併用不可

### ステップ 2.2: 削除

```bash
python shadow_test.py --delete
```

**ナレッジチェック（スライド対応）**: シャドーテストの主な利点は？ → **ユーザーに影響を与えずに新モデルの運用性能を検証できる**

---

## パート 3: オートスケーリング（10分）

### ステップ 3.1: ターゲット追跡ポリシーを設定

パート 1 の A/B エンドポイント（`VariantA`）が起動している状態で実行します。

```bash
python autoscaling_demo.py
```

- **スケーラブルターゲット**を登録（min=1, max=4）
- 予定義メトリクス **`SageMakerVariantInvocationsPerInstance`** で目標値 70 を維持
- スケーリング方法（スライド対応）: ターゲット追跡 / ステップ / スケジュール / オンデマンド

### ステップ 3.2: 登録解除

```bash
python autoscaling_demo.py --delete
```

---

## パート 4: ブルー/グリーンデプロイ（15分）

### ステップ 4.1: Canary トラフィックシフトで更新

```bash
python blue_green_deploy.py
```

- 初期（ブルー）エンドポイントを作成後、**Canary**（50% 先行 + ベイク期間）で新設定に更新
- トラフィックシフトパターン（スライド対応）:

| パターン | 内容 |
|---------|------|
| All at once | 一度に全トラフィックを新環境へ（最速・最小コスト） |
| Canary | 一部を先行、ベイク期間の監視後に残りをシフト |
| Linear | 一定割合ずつ等間隔でシフト（リスク分散） |

- CloudWatch アラームと組み合わせると**自動ロールバック**が可能

### ステップ 4.2: 削除

```bash
python blue_green_deploy.py --delete
```

---

## パート 5: マルチアカウント戦略（考察のみ）

スクリプト実行は不要です（スライド対応）。

- シングルアカウント vs マルチアカウント: 環境分離・影響範囲の限定
- ML 運用モデル: 一元化 / 分散型 / フェデレーテッド
- ベストプラクティス: AWS Organizations / AWS Control Tower / IAM Identity Center

**議論（スライド対応）**: 組織の成長に合わせてパイプラインを複数アカウントに分割するには？

---

## 全リソースの削除（重要）

```bash
python ab_test_variants.py --delete
python shadow_test.py --delete
python autoscaling_demo.py --delete
python blue_green_deploy.py --delete
# または
cd ~/handson && bash cleanup_all.sh
```

---

## ナレッジチェック（スライド対応）

1. マルチアカウント戦略のセキュリティのベストプラクティスは？ → **リソースを分け、アカウント間でアクセスを制限する**
2. 複数モデルをホストするコストを削減できるエンドポイントは？ → **複数モデルエンドポイント**
3. 本番バリアントのルーティング方法は？（2 つ）→ **加重（ランダム）ルーティング / TargetVariant による直接指定**
4. 一部シフト → ベイク期間 → 残りシフト のパターンは？ → **Canary**

---

## 参考ドキュメント

- [Shadow tests](https://docs.aws.amazon.com/sagemaker/latest/dg/shadow-tests.html)
- [Production variants (A/B testing)](https://docs.aws.amazon.com/sagemaker/latest/dg/model-ab-testing.html)
- [Automatically scale Amazon SageMaker AI models](https://docs.aws.amazon.com/sagemaker/latest/dg/endpoint-auto-scaling.html)
- [Blue/Green deployments](https://docs.aws.amazon.com/sagemaker/latest/dg/deployment-guardrails-blue-green.html)
