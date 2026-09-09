"""
モジュール 2: SageMaker Domain の確認
--------------------------------------
SageMaker Studio の実験環境は「Domain」を中心に構成されます。
このスクリプトは既存の Domain・ユーザープロファイル・スペースを一覧表示し、
標準化された実験環境の構成要素を確認します。

  - Domain: チームの共有環境（VPC・実行ロール・認証方式などの設定）
  - ユーザープロファイル: Domain 内の個々のユーザー設定
  - スペース: Studio アプリ（JupyterLab など）を実行する単位

Domain が存在しなくてもエラーにはなりません（Initial フェーズの確認用）。

実行:
    python list_sagemaker_domains.py
"""

import sys
import os
import boto3

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import REGION, banner


def main():
    banner("SageMaker Domain の確認")
    sm = boto3.client("sagemaker", region_name=REGION)

    domains = sm.list_domains().get("Domains", [])
    if not domains:
        print("SageMaker Domain はまだ作成されていません。")
        print("→ Studio を使う場合は、コンソールまたは AWS Service Catalog から")
        print("  標準化された Domain をプロビジョニングします（ラボ 1 のテーマ）。")
        _print_concepts()
        return

    for d in domains:
        did = d["DomainId"]
        print(f"\nDomain: {d.get('DomainName')} ({did})  status={d.get('Status')}")

        profiles = sm.list_user_profiles(DomainIdEquals=did).get("UserProfiles", [])
        print(f"  ユーザープロファイル数: {len(profiles)}")
        for p in profiles:
            print(f"    - {p.get('UserProfileName')}  status={p.get('Status')}")

        spaces = sm.list_spaces(DomainIdEquals=did).get("Spaces", [])
        print(f"  スペース数: {len(spaces)}")
        for s in spaces:
            print(f"    - {s.get('SpaceName')}  status={s.get('Status')}")

    _print_concepts()


def _print_concepts():
    print("\n" + "-" * 60)
    print(" 標準化された実験環境のポイント（スライド対応）")
    print("-" * 60)
    items = [
        "ライフサイクル構成: 起動時のパッケージインストール・アイドル自動シャットダウン",
        "SageMaker Role Manager: ペルソナ（データサイエンティスト/MLOps）ごとの権限",
        "セキュリティ: VPC のみ / 顧客管理キー / IAM Identity Center",
        "AWS Service Catalog: 事前設定テンプレートからセルフサービスで環境を作成",
    ]
    for it in items:
        print(f"  - {it}")


if __name__ == "__main__":
    main()
