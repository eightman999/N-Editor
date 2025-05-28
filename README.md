# n-editor

[![Python Version](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE) n-editorは、主に Paradox Interactive 社のグランドストラテジーゲーム、特に Hearts of Iron IV (HOI4) のMOD（Modification）制作用に設計されたPython (PyQt5) 製のデスクトップアプリケーションです。

## 概要

n-editorは、HOI4などで用いられる特定のテキストベースのスクリプトファイル（州ファイル、戦略地域ファイル、海軍編成ファイル、国家定義ファイルなど）を解析し、ユーザーがグラフィカルユーザーインターフェース（GUI）を通じてこれらのファイルを効率的に編集できるようにすることを目的としています。

## 主な機能

n-editor は以下のゲーム内要素の編集をサポートしています：

* **州 (States):** 人的資源、建造物、勝利ポイント、その他州に関連するプロパティの編集。
* **戦略地域 (Strategic Regions):** 州のグルーピング、天候設定などの編集。
* **海軍OOB (Naval Orders of Battle):**
    * 艦隊構成の編集。
    * 艦船設計の作成と編集。
    * 船体テンプレートの管理。
* **装備 (Equipments):** 陸海空軍の装備の性能や特性の編集。
* **国家の色 (Country Colors):** ゲーム内マップやUIで表示される国家の色の定義。
* **その他:**
    * 国家タグの管理。
    * 師団名のテンプレート編集。
    * イベント効果に関連するスクリプトの簡易編集サポート。
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