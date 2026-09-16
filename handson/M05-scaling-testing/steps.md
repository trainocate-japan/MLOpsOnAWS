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

**A/B テストとシャドーテストの違い**: A/B は両モデルの実応答を比較。シャドーは応答を返さない。

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

シャドーテストの主な利点は、ユーザーに影響を与えずに新モデルの運用性能を検証できる点です。

---

## パート 3: オートスケーリング（20分）

パート 1 の A/B エンドポイント（`mlops-handson-abalone-ab` の `VariantA`）が
**InService** の状態で実行します。まだの場合は先に `python ab_test_variants.py` を実行してください。

### ステップ 3.1: ターゲット追跡ポリシーを設定し、負荷でスケールアウトさせる

```bash
python autoscaling_demo.py
```

このスクリプトは 1 回の実行で次を連続して行います。

1. **スケーラブルターゲットを登録**（min=1, max=4）
2. **ターゲット追跡ポリシーを設定**
   - 予定義メトリクス **`SageMakerVariantInvocationsPerInstance`**
   - 目標値 **10 invocations/instance/分**（スケールアウトを起こしやすくするため低めに設定）
   - スケールアウト クールダウン 60 秒 / スケールイン クールダウン 300 秒
3. **負荷を発生**（4 スレッドで `invoke_endpoint` を連打）
4. **スケールアウトを観察**（`CurrentInstanceCount` を 15 秒ごとにポーリング表示）

- インスタンス数が `1 → 2`（以上）に増えれば**スケールアウト成功**です。
- スケーリングの根拠となった **CloudWatch アラーム**や**スケーリングアクティビティ**が末尾に表示されます。

> **観察のポイント**: 負荷をかけてから実際にインスタンスが増えるまでには**数分の遅延**があります。
> これは、CloudWatch にメトリクスが集計・反映され（1分粒度）、アラームがしきい値超過を検知し、
> Auto Scaling がインスタンスを起動する、という一連の流れに時間がかかるためです。
> オートスケーリングは**急峻なスパイクへの即応**ではなく、**継続的な負荷変動への追従**に向いていることを押さえます。

**議論**: スパイク的な負荷に即応したい場合はどうする？（プロビジョンドキャパシティ、余裕を持たせた最小台数、事前のスケジュールスケーリング など）

### ステップ 3.2: （任意）設定のみ行い、負荷は手動でかける

負荷生成を自動で走らせず、ポリシー設定だけ行いたい場合:

```bash
python autoscaling_demo.py --configure-only
```

その後、別ターミナルから任意のツール（例: 繰り返し `invoke_endpoint` するスクリプトや負荷ツール）で
負荷をかけ、マネジメントコンソールの **CloudWatch** や **エンドポイントのインスタンス数**で観察できます。

### ステップ 3.3: 登録解除

```bash
python autoscaling_demo.py --delete
```

- ターゲット追跡**ポリシー**とスケーラブル**ターゲット**の両方を削除します。
- エンドポイント自体は残るため、不要なら `python ab_test_variants.py --delete` も実行してください。

---

## パート 4: ブルー/グリーンデプロイ（15分）

### ステップ 4.1: Canary トラフィックシフトで更新

```bash
python blue_green_deploy.py
```

- 初期（ブルー）エンドポイントを作成後、**Canary**（50% 先行 + ベイク期間）で新設定に更新
- トラフィックシフトパターン:

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

スクリプト実行は不要です。

- シングルアカウント vs マルチアカウント: 環境分離・影響範囲の限定
- ML 運用モデル: 一元化 / 分散型 / フェデレーテッド
- ベストプラクティス: AWS Organizations / AWS Control Tower / IAM Identity Center

**議論**: 組織の成長に合わせてパイプラインを複数アカウントに分割するには？

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

## 参考ドキュメント

- [Shadow tests](https://docs.aws.amazon.com/sagemaker/latest/dg/shadow-tests.html)
- [Production variants (A/B testing)](https://docs.aws.amazon.com/sagemaker/latest/dg/model-ab-testing.html)
- [Automatically scale Amazon SageMaker AI models](https://docs.aws.amazon.com/sagemaker/latest/dg/endpoint-auto-scaling.html)
- [Blue/Green deployments](https://docs.aws.amazon.com/sagemaker/latest/dg/deployment-guardrails-blue-green.html)
