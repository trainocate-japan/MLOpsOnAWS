# モジュール 6: Reliable MLOps - モニタリング - ハンズオンシナリオ

## シナリオ概要

AnyCompany Consulting のアワビ予測モデルは本番稼働中ですが、時間の経過とともに
入力データの傾向が変わり（例: 別の産地のアワビが増える）、予測精度が徐々に低下する恐れがあります。
あなたは MLOps エンジニアとして、**データドリフトを検知して自動で対処する**仕組みを構築します。

このモジュールでは、エンドポイントのデータキャプチャを有効化し、SageMaker Model Monitor で
ベースラインを作成し、ドリフトを検知したときの再学習・トラブルシューティングのアプローチを学びます。

> **重要**: Amazon SageMaker AI – Model Monitor は **新規のお客様には公開されていません**
> （既存のお客様は継続利用可）。そのため**監視スケジュールを新規作成できません**。
> 本ハンズオンはベースライン生成までを実行し、スケジュールの代替として
> 「キャプチャデータを constraints.json と突き合わせる」方法でドリフト検知の考え方を学びます。
> AWS 公式の推奨代替は、オープンソースの SageMaker AI monitoring solutions
> （MLflow Apps + Evidently AI）＋ Amazon QuickSight ＋ Amazon CloudWatch です。
> 参照: [Model Monitor availability change](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor-availability-change.html)

## 学習目標

このハンズオンを完了すると、以下ができるようになります。

1. **データキャプチャを設定する**: エンドポイントの入力/出力を S3 にキャプチャする
2. **ベースラインを作成する**: 学習データから統計と制約のベースラインを生成する
3. **ドリフト検知の仕組みを理解する**: キャプチャデータをベースライン（constraints.json）と比較する（Model Monitor のスケジュールは新規顧客に非公開のため、代替手段も理解する）
4. **ドリフトを発生させる**: 分布をずらしたトラフィックでドリフトをシミュレートする
5. **再学習アプローチを説明する**: イベント駆動 / スケジュール / オンデマンド
6. **リネージでトラブルシュートする**: Lineage Tracking で関連アーティファクトを特定する

## モデル監視の流れ

```
データキャプチャ有効化 → ベースライン作成 → （比較）→ ドリフト検知 → 通知/再学習
```

- 本来は「ベースライン作成 → 監視スケジュール → 自動でドリフト検知」の流れですが、
  Model Monitor のスケジュールが新規顧客に非公開のため、本ハンズオンでは
  「キャプチャデータと constraints.json を比較する」ステップで検知の考え方を学びます。
- 定期実行・可視化が必要な場合は、AWS 公式推奨の代替（オープンソースの
  SageMaker AI monitoring solutions〔MLflow Apps + Evidently AI〕＋ QuickSight ＋ CloudWatch）で置き換えます。

## 再学習のアプローチ

| アプローチ | 契機 |
|-----------|------|
| イベント駆動 | メトリクスのしきい値超過・状況の変化 |
| オンデマンド | 事業の変化に基づいて手動で |
| スケジュール | 指定された日時に定期的に |

## 使用する AWS サービス

- Amazon SageMaker Model Monitor（データキャプチャ、ベースライン生成）※監視スケジュールは新規顧客に非公開（作成不可）
- Amazon SageMaker AI（エンドポイント）
- Amazon CloudWatch（メトリクス・アラーム）
- Amazon S3（キャプチャデータ・ベースライン結果）

## 所要時間

約 60 分

## 前提条件

- M02 でモデルアーティファクトが作成済みであること
- `SAGEMAKER_ROLE_ARN` が設定されていること

> 監視エンドポイントは起動中ずっと課金されます。**完了後は必ず削除**してください
> （`python enable_data_capture.py --delete`）。
