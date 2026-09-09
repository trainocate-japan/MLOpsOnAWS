# デモ環境インフラストラクチャ

## 概要

「MLOps Engineering on AWS」研修のハンズオン用デモ環境です。
Session Manager 経由で接続する EC2 を使用し、SSH キーは不要です。
ハンズオン資材は S3 バケットに保管し、EC2 起動時に自動でダウンロードします。

- 接続: AWS Systems Manager Session Manager（インバウンドポート開放なし）
- 実行環境: Amazon Linux 2023 + Python 3.12 venv（boto3 / sagemaker SDK / pandas / scikit-learn プリインストール）
- SageMaker 実行ロール: トレーニング / エンドポイント / パイプライン / Model Monitor に渡す `MLOpsHandsonSageMakerRole` を自動作成（ARN は `SAGEMAKER_ROLE_ARN` 環境変数で提供）
- コスト削減: 毎日 23:00 JST に EC2 を自動停止（EventBridge + Lambda）

## 初回セットアップ

リポジトリをクローンした後、以下を 1 回実行してください：

```bash
git config core.hooksPath .githooks
chmod +x infra/upload-assets.sh .githooks/pre-push
```

これにより `git push` 時に `handson/` フォルダに変更があれば自動で S3 にアップロードされます。

## デプロイ手順

### Step 1: 資材を S3 にアップロード

```bash
./infra/upload-assets.sh
```

初回はバケット `mlops-handson-assets-<ACCOUNT_ID>` を作成し、`handson/` を tar.gz でアップロードします。

### Step 2: CloudFormation スタックの作成

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws cloudformation create-stack \
  --stack-name mlops-handson-demo-env \
  --template-body file://infra/demo-ec2.yaml \
  --parameters \
    ParameterKey=AssetsBucket,ParameterValue=mlops-handson-assets-$ACCOUNT_ID \
    ParameterKey=AssetsPrefix,ParameterValue=handson-assets \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

> AMI は SSM パラメータ（`/aws/service/ami-amazon-linux-latest/...`）で自動解決されるため、リージョンごとに AMI ID を指定する必要はありません。

### Step 3: 完了を待機

```bash
aws cloudformation wait stack-create-complete --stack-name mlops-handson-demo-env --region us-east-1
```

### Step 4: Session Manager で接続

```bash
# インスタンス ID を取得
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name mlops-handson-demo-env \
  --query "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue" \
  --output text)

# 接続
aws ssm start-session --target $INSTANCE_ID

# 接続後（自動で venv 有効化 & ~/handson に移動）
cd ~/handson
echo $SAGEMAKER_ROLE_ARN   # SageMaker 実行ロール ARN が表示される
```

### SageMaker 実行ロール ARN の確認

ハンズオンのスクリプトは、トレーニングジョブやエンドポイントに渡す SageMaker 実行ロールを
`SAGEMAKER_ROLE_ARN` 環境変数から取得します。EC2 デモ環境では自動設定済みです。
ローカルや SageMaker Studio で実行する場合は、以下で取得したロール ARN を設定してください。

```bash
# CloudFormation 出力から取得
aws cloudformation describe-stacks --stack-name mlops-handson-demo-env \
  --query "Stacks[0].Outputs[?OutputKey=='SageMakerRoleArn'].OutputValue" --output text

# 環境変数に設定
export SAGEMAKER_ROLE_ARN=arn:aws:iam::<ACCOUNT_ID>:role/MLOpsHandsonSageMakerRole
```

> SageMaker Studio 内で実行する場合は、`sagemaker.get_execution_role()` が自動で
> ドメインの実行ロールを返すため、環境変数の設定は不要です。

## 運用フロー

```
初回:   upload-assets.sh → CFn create-stack → 接続確認
前日:   aws ec2 start-instances --instance-ids <ID>
当日:   aws ssm start-session → cd ~/handson
夜間:   23:00 JST に自動停止（Lambda）
更新時: upload-assets.sh → 起動中の EC2 は SSM 経由で自動再取得
```

## 資材の更新方法

ハンズオン内容を更新した場合は、`upload-assets.sh` を実行すれば S3 に最新版がアップロードされ、
起動中の EC2 インスタンスには SSM Run Command 経由で自動反映されます。

停止中のインスタンスに手動反映する場合：

```bash
aws ssm start-session --target <INSTANCE_ID>
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 cp s3://mlops-handson-assets-$ACCOUNT_ID/handson-assets/handson.tar.gz /tmp/
rm -rf ~/handson && mkdir ~/handson
tar -xzf /tmp/handson.tar.gz -C ~/handson --strip-components=1
```

## コスト見積もり

| リソース | 月間コスト（研修時のみ起動） |
|---------|--------------------------|
| EC2 t3.large（1日8時間×3日） | ~$9 |
| EBS 30GB gp3 | ~$2.40 |
| S3（資材保管） | < $0.10 |
| Lambda（自動停止） | < $0.01 |
| SageMaker トレーニング/エンドポイント（ハンズオン実行） | $5-15/研修回 |
| **合計** | **~$17-27/月** |

> SageMaker のリアルタイムエンドポイントは起動中は課金されます。
> 各モジュールのハンズオン完了後、および研修終了後は必ず削除してください（`handson/cleanup_all.sh`）。

## クリーンアップ

```bash
# 各モジュールで作成した SageMaker リソースを先に削除
cd handson && bash cleanup_all.sh && cd ..

# スタック削除
aws cloudformation delete-stack --stack-name mlops-handson-demo-env --region us-east-1
aws cloudformation wait stack-delete-complete --stack-name mlops-handson-demo-env --region us-east-1

# S3 バケット削除
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws s3 rb s3://mlops-handson-assets-$ACCOUNT_ID --force
```

各モジュールで作成した SageMaker リソース（エンドポイント / モデル / Model Package Group /
Feature Group / Pipeline / Monitoring Schedule など）は
`handson/cleanup_all.sh` で一括削除できます。
