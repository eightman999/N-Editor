# NavalDesignSystem (NDS)

[![Python Version](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE) NDSは、主に Paradox Interactive 社のグランドストラテジーゲーム、特に Hearts of Iron IV (HOI4) のMOD（Modification）制作用に設計されたPython (PyQt5) 製のデスクトップアプリケーションです。

## 概要

NDSは、HOI4などで用いられる特定のテキストベースのスクリプトファイル（州ファイル、戦略地域ファイル、海軍編成ファイル、国家定義ファイルなど）を解析し、ユーザーがグラフィカルユーザーインターフェース（GUI）を通じてこれらのファイルを効率的に編集できるようにすることを目的としています。

## 主な機能

NDS は以下のゲーム内要素の編集をサポートしています：

* **海軍OOB (Naval Orders of Battle):**
    * 艦隊構成の編集。
    * 艦船設計の作成と編集。
    * 船体テンプレートの管理。
* **装備 (Equipments):** 海軍の装備の性能や特性の編集。
* **MOD管理:** 編集対象のMODを選択し、バニラデータとMODデータを区別して扱えます。 (`views/mod_selector_widget.py`)

## 技術スタック

* **プログラミング言語:** Python 3
* **GUIフレームワーク:** PyQt5
* **パーサー:** [PLY (Python Lex-Yacc)](https://www.dabeaz.com/ply/) を利用したカスタムパーサー群 (`parser/` ディレクトリ)
    * `StateParser.py`: 州ファイル用パーサー
    * `StrategicRegionParser.py`: 戦略地域ファイル用パーサー
    * `NavalOOBParser.py`: 海軍編成ファイル用パーサー
    * `CountryColorParser.py`: 国家色ファイル用パーサー
    * `EffectParser.py`: イベント効果など、汎用的な効果記述用パーサー (部分的なサポート)
* **設定ファイル:** 一部で YAML (`equipments_templates.yml`) を使用。

## プロジェクト構造

プロジェクトは、MVC（Model-View-Controller）に近い構造を採用しています。

* `main.py`: アプリケーションのエントリーポイント。
* `views/`: PyQt5ベースのUIコンポーネント (`main_window.py`, `state_view.py` など)。
* `controllers/`: アプリケーションロジックとUIイベント処理 (`app_controller.py` など)。
* `models/`: データ構造の定義と状態管理 (`data_models.py`, `equipment_model.py`, `app_settings.py` など)。
* `parser/`: ゲームファイル形式を解析するためのパーサーモジュール。
* `EXAMPLE/`: 各種編集対象ファイルのサンプル。MOD制作時の参考になります。
* `assets/`: アイコンなどのリソースファイル。

## 対象ファイル形式

主に `.txt` 形式ですが、Hearts of Iron IV特有のキー・バリュー形式のネストされた構造（Paradox Development Studio Script）を持っています。
例:
```pds
state={
    id=1
    name="STATE_1"
    manpower=1000000
    history={
        owner = GER
        add_core_of = GER
    }
    # ...その他のプロパティ
}
```

### NavalDesignSystem - データ同期機能セットアップガイド
## 概要
  NavalDesignSystemにデータ同期機能が追加されました。この機能により、装備・船体・設計・艦隊データをGitHub等のオンラインリポジトリと自動同期できます。
## 主な機能

  自動同期: データ保存時に自動でローカルコミット
  手動同期: ボタンクリックでプッシュ/プル実行
  終了時同期: アプリ終了時に自動でリモートと同期
  競合回避: Gitベースの安全な同步機構

## セットアップ手順
1. GitHubリポジトリの準備
  ```bash
  # 1. GitHubで新しいリポジトリを作成
  # 2. ローカルでgit設定（初回のみ）
  git config --global user.name "あなたの名前"
  git config --global user.email "your-email@example.com"
  ```
2. パーソナルアクセストークンの取得

  GitHub → Settings → Developer settings → Personal access tokens
  "Generate new token (classic)" をクリック

以下の権限を付与:

  repo (フルアクセス)
  user (読み取り)


トークンをコピー（後で必要）

3. NavalDesignSystemでの設定

  アプリを起動
  ツールバーの "⚙️ 同期設定" をクリック
  以下を入力:

  GitHubリポジトリURL: https://github.com/username/repository.git
  GitHubトークン: 先ほど取得したトークン
  Gitユーザー名: あなたの名前
  Gitメール: あなたのメールアドレス


### オプション設定:

  ☑️ 保存時に自動コミット: 推奨
  ☑️ 終了時に自動同期: 推奨
  
  
  "接続テスト" で動作確認
  "OK" で設定完了

## 使用方法
### 基本的な同期操作
  ボタン機能説明🔄 同期完全同期プル→プッシュの完全同期⬆️ プッシュアップロードローカル → リモート⬇️ プルダウンロードリモート → ローカル
  自動同期

  保存時: 装備・船体・設計・艦隊データを保存すると自動でローカルコミット
  終了時: アプリ終了時に自動でリモートにプッシュ

  ステータス確認

  ステータスバー: 右下に同期状態を表示
  
  🟢 同期先: repository-name - 設定完了
  🔴 同期未設定 - 設定が必要
  
  
  プログレスバー: 同期実行中に進捗を表示

## トラブルシューティング
### よくあるエラーと対処法
1. 認証エラー
  fatal: Authentication failed
  対処法:

    GitHubトークンが正しいか確認
    トークンの権限設定を確認
    トークンの有効期限を確認

2. リポジトリが見つからない
fatal: repository not found
対処法:

リポジトリURLが正しいか確認
リポジトリが公開されているか確認
アクセス権限があるか確認

3. 競合エラー
Your branch and 'origin/main' have diverged
対処法:

"⬇️ プル" で最新データを取得
競合があれば手動で解決
"⬆️ プッシュ" で変更をアップロード

4. ネットワークエラー
fatal: unable to access
対処法:

インターネット接続を確認
プロキシ設定を確認
しばらく時間をおいて再試行

デバッグ機能
メニューバー → "同期" から以下の機能が利用できます:

同期状態確認: 現在の設定状況を表示
強制同期: 強制的に同期を実行
同期履歴: 過去の同期履歴を表示

高度な使用方法
SSH認証の使用
GitHubトークンの代わりにSSH認証も使用できます:
```bash# SSH鍵生成（初回のみ）
ssh-keygen -t ed25519 -C "your-email@example.com"

# 公開鍵をGitHubに登録
cat ~/.ssh/id_ed25519.pub
リポジトリURLにSSH形式を使用:
git@github.com:username/repository.git
```
チーム開発での注意点

競合を避ける:

同じファイルを同時編集しない
定期的にプルして最新状態を保つ


命名規則:

装備ID、船体ID等は重複しないよう調整
プレフィックスで担当者を区別


ブランチ戦略:

大きな変更は別ブランチで作業
プルリクエストでレビュー



データ構造
同期されるデータ (参照: [NDSDB](https://github.com/eightman999/NDSDB)):
```
data/
├── designs/                 # 艦の設計定義
├── equipments/              # 装備データ (SMAA, SMLG など)
├── equipments_templates.yml # 装備タイプのフィールド構造
├── hulls_backup_*           # 船体データのバックアップ
├── fleets/                  # 艦隊編成情報
└── convert_*.py             # YAML→JSON 変換スクリプト
```
セキュリティ考慮事項

トークン管理: アクセストークンは適切に管理し、定期的に更新
公開リポジトリ: 機密データは公開リポジトリに保存しない
アクセス制御: 必要最小限の権限のみ付与

まとめ
この同期機能により、複数のPC間でのデータ共有、チームでのMOD制作、データのバックアップが簡単に実現できます。
何か問題が発生した場合は、デバッグメニューから状態を確認し、必要に応じて強制同期を実行してください。
