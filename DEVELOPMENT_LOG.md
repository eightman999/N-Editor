# 開発ログ

## 2025年6月16日 (月)

### ✅ ship_type:role_type双方向制約システム実装
**時刻**: 14:30-15:00
**概要**: 船体登録および設計において、ship_type(船体種別)とrole_type(archetype)の双方向制約関係を実装

**実装内容**:
- **制約マッピング**: `SHIP_ROLE_CONSTRAINTS`で船体種別ごとに利用可能なrole_typeを定義
- **船体登録制約**: 種別選択時にarchetypeの選択肢を自動制限
- **逆方向制約**: archetype選択時にship_typeの選択肢を自動制限
- **設計時検証**: 船体選択時と保存時に制約違反をチェック
- **制約関数**: 制約チェック用のユーティリティ関数群

**制約例**:
- BB(一等戦艦): BB, B, BC, FBB, BBG, SB, PB, IC, ACR, CDB, CA, CB, BM, CG (14種類)
- BF(航空戦艦): BF のみ (1種類)
- CF(航空巡洋艦): CF のみ (1種類)
- SCV(潜水空母): SCV のみ (1種類)

**技術特徴**:
- **双方向制約適用**: ship_type ⇄ archetype の相互制限
- **動的制約適用**: 選択変更時のリアルタイム選択肢更新
- **制約違反検出**: 保存時・選択時の自動検証
- **逆引き機能**: `get_ship_types_for_role()` によるarchetype→ship_type検索
- **レガシー対応**: 既存船体データとの互換性維持
- **デバッグ支援**: 制約違反時の詳細ログ出力

**ファイル**:
- `utils/ship_role_constraints.py`: 制約定義と双方向検索関数
- `views/hull_form.py`: 双方向制約機能追加
- `views/design_view.py`: 船体選択・保存時制約チェック追加

**影響範囲**: 船体登録と設計の整合性向上、不正な組み合わせの防止

### ✅ DesignView艦種選択をarchetype基準に変更
**時刻**: 15:15
**概要**: DesignViewの艦種選択プルダウンをship_typeからarchetypeベースに変更

**実装内容**:
- **艦種選択基準変更**: ship_type_mapping → archetype (pdx_tools.pdx_ssw.ship_types)
- **フィルタリング更新**: 船体選択時にarchetypeで直接フィルタリング
- **検索クエリ更新**: archetypeに基づくWeb検索クエリ生成
- **UI整合性**: 選択された船体のarchetypeとUI選択状態の同期

**技術特徴**:
- **直接archetype選択**: 中間層なしでarchetypeを直接選択
- **制約整合性**: 船体のarchetype制約チェックとUI選択の一致
- **アイコン対応**: archetypeごとのアイコン表示
- **検索連動**: archetype選択に基づく適切な英語検索クエリ

**ファイル**:
- `views/design_view.py`: 艦種選択をarchetype基準に変更

**影響範囲**: DesignViewの船体選択がより正確になり、archetype制約との整合性が向上

### ✅ DesignView船体選択に制約ベースフィルタリング実装
**時刻**: 15:30
**概要**: DesignViewでarchetype選択時に、SHIP_ROLE_CONSTRAINTSに基づく厳密なフィルタリングを実装

**実装内容**:
- **3段階フィルタリング**: archetype一致、ship_type許可、内部制約の三重チェック
- **制約ベース検索**: 選択archetypeで利用可能なship_typeリストを動的取得
- **詳細ログ出力**: フィルタリング条件と除外理由の詳細表示
- **整合性保証**: 表示される船体が全て制約に適合することを保証

**フィルタリング条件**:
1. **archetype一致**: 船体のarchetype = 選択されたarchetype
2. **ship_type許可**: 船体のship_typeが選択archetypeで許可されている
3. **内部制約**: 船体内でship_type:archetypeの組み合わせが有効

**技術特徴**:
- **動的制約適用**: get_ship_types_for_role()による逆引き制約チェック
- **三重検証**: 複数条件での厳密な適合性チェック
- **デバッグ支援**: 詳細な除外理由とログ出力
- **制約違反防止**: 不正な組み合わせの船体を完全に除外

**ファイル**:
- `views/design_view.py`: 制約ベースフィルタリングロジック実装

**影響範囲**: DesignViewで表示される船体が制約に完全準拠し、不正な組み合わせが排除される

## 2025年6月14日 (土)

### ✅ 海軍OOBファイル書き出し機能実装
**時刻**: 15:30
**概要**: HOI4海軍編成データ(OOB)の書き出し機能を完全実装

**実装内容**:
- **データモデル**: Ship, TaskForce, Fleetクラスをdata_models.pyに追加
- **書き出しコントローラー**: NavalExportControllerクラスで階層構造書き出し機能を実装
- **ユーザーインターフェース**: NavalExportDialogで直感的な操作性を提供
- **メインウィンドウ統合**: エクスポートメニューと機能呼び出しを実装
- **包括的検証**: データ検証とエラーハンドリングシステム

**技術特徴**:
- **階層構造書き出し**: units → fleet → task_force → ship → equipment
- **インデント管理**: タブベースの適切な階層表現
- **文字列エスケープ**: 特殊文字の安全な処理
- **非同期処理**: 重い書き出し処理のワーカースレッド実装
- **プログレス表示**: リアルタイム進捗表示とキャンセル機能
- **サンプルデータ**: テスト用の大和型戦艦サンプル生成

**ファイル**:
- `models/data_models.py`: 海軍データモデル追加
- `controllers/naval_export_controller.py`: 新規作成
- `views/naval_export_dialog.py`: 新規作成  
- `views/main_window.py`: エクスポートメニュー統合

**影響範囲**: 新機能追加のため既存機能への影響なし

### ✅ FleetView統合: 設計した艦隊編成の直接書き出し機能
**時刻**: 16:15
**概要**: FleetViewで設計した艦隊編成を直接HOI4形式で書き出せる機能を実装

**実装内容**:
- **データ変換システム**: FleetViewの内部データをShip/TaskForce/Fleetモデルに自動変換
- **UI統合**: FleetViewに「HOI4形式で書き出し」ボタンを追加
- **智能的艦種推定**: 設計名から艦種を自動判定（駆逐艦、巡洋艦、戦艦等）
- **複数艦隊対応**: 複数艦隊がある場合の選択ダイアログ
- **シームレス連携**: FleetView→NavalExportDialogへの直接データ受け渡し

**技術特徴**:
- **FleetViewExportHelper**: データ変換を専門に行うヘルパークラス
- **艦種マッピング**: 設計名のキーワードから適切な艦種を推定
- **装備自動生成**: 艦種と国家コードに基づく装備データ自動作成
- **エラーハンドリング**: 変換プロセス全体の堅牢なエラー処理
- **選択的書き出し**: 複数艦隊から特定艦隊を選択して書き出し

**ワークフロー改善**:
1. FleetViewで艦隊編成を設計
2. 「HOI4形式で書き出し」ボタンをクリック
3. 複数艦隊がある場合は対象艦隊を選択
4. NavalExportDialogで設定確認・書き出し実行

**ファイル変更**:
- `views/fleet_view.py`: エクスポートボタン・変換機能・連携ロジック追加

**影響範囲**: FleetViewの機能拡張、既存機能への影響なし

### ✅ HOI4 MOD形式エクスポートシステム実装
**時刻**: 17:00
**概要**: Naval Design Systemで設計した艦船データをHearts of Iron IV（HOI4）のMODファイル形式でエクスポートする包括的なシステムを実装

**実装内容**:
- **エクスポーターモジュール**: 拡張可能な基底クラスとHOI4専用エクスポーター
- **性能計算エンジン**: モジュール、船体、アップグレードを統合した総合性能計算
- **高度なUI**: タブ式設定ダイアログとリアルタイム進捗表示
- **データ統合**: AppController経由での設計・船体データ一括取得
- **メニュー統合**: メインウィンドウに「HOI4 MOD形式エクスポート」メニューを追加

**技術特徴**:
- **create_equipment_variant形式**: 設計データのHOI4バリアント形式出力
- **equipments形式**: 船体定義のHOI4装備ブロック形式出力
- **モジュール性能反映**: 個別モジュールの性能を統合した総合統計計算
- **アップグレード効果**: 各種アップグレードの性能修正を適用
- **派生統計計算**: 戦闘力、生存性、戦略価値、コスト効率の自動計算
- **非同期処理**: 大量データのバックグラウンド処理と進捗表示

**出力ファイル形式**:
- **設計ファイル**: `{country_tag}_designs.txt` - create_equipment_variantブロック
- **船体ファイル**: `{country_tag}_hulls.txt` - equipmentsブロック
- **性能コメント**: 計算された性能値をコメントとして自動挿入
- **エラーハンドリング**: データ検証とバックアップ機能

**ファイル追加**:
- `exporters/`: 新規モジュールディレクトリ
- `exporters/base_exporter.py`: 基底エクスポータークラス
- `exporters/hoi4_exporter.py`: HOI4専用エクスポーター
- `utils/stats_calculator.py`: モジュール性能計算エンジン
- `views/hoi4_export_dialog.py`: 高度なエクスポートダイアログUI

**機能拡張**:
- `views/main_window.py`: HOI4エクスポートメニュー統合
- `controllers/app_controller.py`: エクスポート用データ取得メソッド群追加

**影響範囲**: 新機能追加、既存機能への影響なし

### ✅ DesignView QComboBox削除エラー修正
**時刻**: 22:15
**概要**: 内部スロット削除時にQComboBoxウィジェットの削除タイミング問題で発生するRuntimeErrorを修正

**問題**:
```
RuntimeError: wrapped C/C++ object of type QComboBox has been deleted
```
- 内部スロット削除機能でウィジェット参照が無効になった後のアクセス
- UIレイアウト更新とウィジェット削除の競合状態
- `equipment_combo`へのアクセス時の削除済みオブジェクト参照

**実装内容**:
- **安全なウィジェットアクセス**: 全ての`equipment_combo`アクセスに安全チェック追加
- **例外ハンドリング強化**: `RuntimeError`と`AttributeError`をキャッチ
- **削除処理改善**: ウィジェット削除時の適切な順序とエラーハンドリング
- **表示更新保護**: `_refresh_internal_slots_display()`メソッドの安全性向上

**技術詳細**:
```python
# Before: 直接アクセス（危険）
equipment_combo = slot_info["equipment_combo"]
equipment_text = equipment_combo.currentText()

# After: 安全チェック付きアクセス
try:
    equipment_combo = slot_info.get("equipment_combo")
    if equipment_combo and not equipment_combo.isHidden():
        equipment_text = equipment_combo.currentText()
        if equipment_text != "選択する":
            equipment_info = equipment_text
except (RuntimeError, AttributeError):
    equipment_info = "なし"
```

**影響範囲**:
- views/design_view.py: `remove_internal_slot()`, `_refresh_internal_slots_display()`, `update_equipment_combo()`, `get_form_data()` メソッド
- 内部スロット削除機能の安定性向上
- UIウィジェット管理の堅牢性向上

**期待効果**:
- 内部スロット削除時のクラッシュ防止
- UI操作の安定性向上
- ウィジェットライフサイクル管理の改善

---

### ✅ MOD設計データキャッシュシステム実装
**時刻**: 21:30
**概要**: MOD設計データの読み込み・保存・統計計算処理に包括的なキャッシュシステムを実装

**実装内容**:
- **MODDataCacheManager拡張**: 設計データ専用キャッシュ機能を追加
  - `designs`: 設計ファイル一覧キャッシュ
  - `resolved_designs`: 船体・装備情報を含む解決済み設計データキャッシュ
  - `design_stats`: 設計統計計算結果キャッシュ
- **個別ファイルキャッシュ**: 設計ファイル単位での詳細キャッシュ管理
- **app_controller統合**: 設計読み込み・保存・削除メソッドへのキャッシュ機能統合
- **自動キャッシュ無効化**: ファイル変更検出による適切なキャッシュクリア
- **統計計算キャッシュ**: 重い設計統計計算結果の永続化

**技術詳細**:
```python
# 設計データタイプの追加
DATA_TYPES = {
    'designs': {
        'cache_key': 'designs_cache',
        'directories': ["designs"],
        'file_patterns': ['*.json']
    },
    'resolved_designs': {
        'cache_key': 'resolved_designs_cache', 
        'directories': ["designs", "common/units", "common/units/equipment"],
        'file_patterns': ['*.json', '*.txt']
    },
    'design_stats': {
        'cache_key': 'design_stats_cache',
        'directories': ["designs", "common/units", "common/units/equipment"],
        'file_patterns': ['*.json', '*.txt']
    }
}
```

- **パス解決問題修正**: macOSでの一時ディレクトリパス解決エラー対応
- **キャッシュクリア改善**: 個別設計削除時の適切なキャッシュクリア実装
- **テストスイート作成**: 全機能を検証する包括的テストスイート実装

**影響範囲**:
- utils/mod_data_cache_manager.py: 設計データ専用メソッド追加
- controllers/app_controller.py: load_design, get_all_designs, save_design, delete_design, get_design_stats メソッドのキャッシュ対応
- test_design_cache.py: 新規テストスイート作成

**期待効果**:
- **設計ファイル読み込み**: 2回目以降の読み込みが瞬時に（ファイル解析・ヘッダー検証スキップ）
- **設計一覧表示**: キャッシュヒット時の表示が大幅高速化
- **設計統計計算**: 複雑な計算結果の再利用でUI応答性向上
- **メモリ効率**: ファイル読み込みの重複処理削減

**テスト結果**:
- 基本的な設計キャッシュ機能: ✅
- 設計キャッシュ無効化機能: ✅
- 一括設計データキャッシュ機能: ✅

### ✅ StrategicRegionParser依存関係エラー修正
**時刻**: 23:45
**概要**: StrategicRegionParserが依存するPLY (Python Lex-Yacc) ライブラリの不足により発生していたパーサーエラーを修正

**問題**:
```
ModuleNotFoundError: No module named 'ply'
ParserError: Parsing failed due to syntax error
```
- PLYライブラリ (3.11) が外部管理Python環境にインストールされていなかった
- StrategicRegionParser.pyでのPLYインポートが失敗
- 戦略地域ファイル ("173-Eastern North Sea.txt", "46-Barents Sea.txt") の解析が不可能

**実装内容**:
- **PLY依存関係解決**: `python3 -m pip install --break-system-packages ply==3.11` でPLY 3.11をインストール
- **パーサー動作確認**: 問題のあった戦略地域ファイルでの解析テスト実行
- **機能検証**: 両ファイルの正常な解析を確認

**技術詳細**:
- **requirements.txt確認**: PLY 3.11が必要依存関係として記載されていることを確認
- **環境対応**: macOS外部管理Python環境での適切なライブラリインストール
- **解析テスト**: 実際の戦略地域ファイルコンテンツでの正常動作確認

**テスト結果**:
```python
# 173-Eastern North Sea.txtの解析
Parsing successful!
Result keys: ['id', 'name', 'provinces', 'weather']

# 46-Barents Sea.txtの解析  
Parsing successful for Barents Sea!
Result keys: ['id', 'name', 'provinces', 'weather']
```

**影響範囲**:
- parser/StrategicRegionParser.py: 正常動作復旧
- MOD戦略地域ファイル解析機能: 完全復旧
- PLY依存関係: システム環境への適切なインストール

**期待効果**:
- 戦略地域ファイル解析機能の完全復旧
- MODデータ読み込み処理の安定化
- パーサー関連機能の正常動作保証

---

## 2025年6月12日 (木)

### ✅ FlagSpriteManagerのMOD別ファイル分離機能実装
**時刻**: 18:50
**概要**: 国旗スプライトシートのファイルがMOD間で上書きされる問題を修正し、MOD別にファイルを分離保存する機能を実装

**実装内容**:
- **FlagSpriteManager修正**: `__init__`メソッドにmod_nameパラメータを追加
- **ファイル名にMOD名追加**: `flags_sprite.png` → `{mod_name}_flags_sprite.png`、`flags_coords.json` → `{mod_name}_flags_coords.json`
- **AppController統合**: 現在選択中のMOD名をFlagSpriteManagerに自動で渡す機能追加
- **MOD変更時の自動クリア**: MOD切り替え時にFlagSpriteManagerインスタンスを自動でリセット

**技術詳細**:
```python
# Before: 全MODで同じファイル名（上書きされる）
self.sprite_sheet_path = os.path.join(cache_dir, "flags_sprite.png")
self.coords_file_path = os.path.join(cache_dir, "flags_coords.json")

# After: MOD名を含む個別ファイル名
self.sprite_sheet_path = os.path.join(cache_dir, f"{mod_name}_flags_sprite.png")
self.coords_file_path = os.path.join(cache_dir, f"{mod_name}_flags_coords.json")
```

**影響範囲**:
- utils/flag_sprite_manager.py: コンストラクタとファイルパス生成ロジック
- controllers/app_controller.py: FlagSpriteManager初期化とMOD変更時のクリア処理

**期待効果**:
- 複数MOD使用時の国旗スプライトシート保護
- MOD切り替え時のキャッシュ再利用による性能向上
- 各MOD固有の国旗データ保持

---

### ✅ FleetViewログ重複問題修正
**時刻**: 15:00
**概要**: FleetViewでログが重複出力される問題を修正し、頻繁なログをDEBUGレベルに調整

**実装内容**:
- **ログ重複修正**: `logger.propagate = False`で親ロガーへの伝播を無効化
- **個別ファイル処理ログ**: INFOからDEBUGレベルに変更
- **艦隊データ抽出ログ**: INFOからDEBUGレベルに変更
- **検索結果ログ**: 3件以上の場合のみINFO表示、3件未満はDEBUG表示
- **艦隊表示更新ログ**: 全てDEBUGレベルに変更

**技術詳細**:
- FleetView独自ロガーの伝播設定で重複出力を根本解決
- 頻繁に出力される処理進捗ログをDEBUGレベルに移行
- 重要な検索結果のみINFOレベルで表示

**影響範囲**:
- views/fleet_view.py: ログ設定とレベル調整

**期待効果**:
- ログ重複問題の完全解決
- コンソール出力の大幅なクリーン化
- デバッグ時の詳細ログは維持

---

### ✅ MOD艦艇データ更新ログレベル調整
**時刻**: 14:50
**概要**: MOD艦艇データの更新ログを件数ベースでフィルタリング

**実装内容**:
- **開始ログ**: INFOからDEBUGレベルに変更
- **完了ログ**: 10件以上の場合のみINFO表示、10件未満はDEBUG表示
- **条件ベース表示**: 大量データ処理時のみ重要ログとして表示
- **国家タグ情報追加**: 完了ログに国家タグを追加して識別性向上

**技術詳細**:
- 開始ログ: `logger.info()` → `logger.debug()` に変更
- 完了ログ: `len(ship_list) >= 10` の条件で INFO/DEBUG を切り替え
- ログノイズ削減と重要情報の適切な表示バランス

**影響範囲**:
- controllers/app_controller.py: `refresh_mod_ships()` メソッドのログレベル調整

**期待効果**:
- 少数艦艇の更新時のログノイズ削減
- 大量データ処理時の進捗確認は維持
- コンソール出力の更なるクリーン化

---

### ✅ キャッシュログレベル調整
**時刻**: 14:45
**概要**: 永続キャッシュからのデータ読み込みログをコンソール非表示に変更

**実装内容**:
- **stateデータキャッシュログ**: INFOからDEBUGレベルに変更
- **strategic regionキャッシュログ**: INFOからDEBUGレベルに変更
- **ログ出力抑制**: 頻繁に出力されるキャッシュ読み込みログをコンソールから除外
- **初期化ログ維持**: 重要な初期化ログは INFO レベルを維持

**技術詳細**:
- `logger.info()` → `logger.debug()` に変更
- キャッシュ使用時の詳細情報はデバッグモード時のみ出力
- ユーザビリティ向上とログノイズ削減

**影響範囲**:
- controllers/app_controller.py: キャッシュ読み込みログレベル変更

**期待効果**:
- コンソール出力のクリーン化
- 重要なログメッセージの視認性向上

---

### ✅ DesignView追加スロット削除機能改善
**時刻**: 14:30
**概要**: 船体設計における追加スロットの削除機能を、削除したいスロットを選択可能な方式に改良

**実装内容**:
- **選択可能削除ダイアログ**: 削除したいスロットを個別に選択できるダイアログを実装
- **複数選択対応**: 複数のスロットを一度に削除可能
- **詳細情報表示**: スロット番号、カテゴリー、装備情報を一覧で確認可能
- **確認ダイアログ**: 削除前の確認メッセージで誤操作を防止
- **自動レイアウト更新**: 削除後のスロット番号とレイアウトを自動で再構成
- **全選択・選択解除**: 操作の利便性向上

**技術詳細**:
- QListWidget with MultiSelectionでスロット選択UI実装
- インデックス降順ソートで後ろから削除し、配列操作の整合性を保持
- `_refresh_internal_slots_display()`メソッドで表示の完全再構築
- スロットID、カテゴリー選択状態、装備選択状態の一括更新

**影響範囲**:
- views/design_view.py: `remove_internal_slot()`メソッドの全面改修
- `_refresh_internal_slots_display()`メソッド新規追加
- 内部スロット管理の堅牢性向上

**期待効果**:
- ユーザビリティの大幅向上
- 設計作業の効率化
- 誤操作によるスロット削除の防止

---

### ✅ Web検索機能の内部ブラウザ完全実装
**時刻**: 14:00
**概要**: Web検索機能を外部ブラウザ依存から内部完結型に大幅改良

**実装内容**:
- **内部Webスクレイピング**: requests + BeautifulSoup4による検索結果取得
- **複数検索エンジン対応**: Google、DuckDuckGo、Wikipedia等の結果解析
- **フォールバック機能**: 依存関係不足時の代替リンク表示
- **テキスト選択・コピー**: 数値等のコピペしやすいCSS設定
- **リンク内部処理**: 全てのリンクを内部ブラウザで開く機能
- **相対URL処理**: Googleリダイレクト等の適切な解決
- **エラーハンドリング**: ICUエラー対応と安定性向上

**技術詳細**:
- DuckDuckGoをデフォルト検索エンジンに変更（解析しやすさ）
- 複数CSSセレクタパターンでGoogle検索結果を確実に抽出
- ページ履歴管理とナビゲーション機能
- 依存関係チェックと自動フォールバック

**影響範囲**:
- utils/web_search_widget.py: 全面的な機能強化
- 検索結果表示の大幅改善
- ユーザビリティ向上

**期待効果**:
- 完全な内部検索環境の実現
- データ参照作業の効率化

---

### ✅ 装備・船体フォームへのdescription項目追加
**時刻**: 13:30
**概要**: Naval Design Systemの装備・船体追加機能にdescription項目を実装

**実装内容**:
- **装備フォーム**: equipment_form.pyのcommon_fieldsにdescription追加
- **船体フォーム**: hull_form.pyにdescription_edit QLineEdit追加
- **データ管理**: get_form_data()、set_form_data()、clear_form()メソッド対応
- **モデル互換性**: 既存のJSONベース保存/読み込みで自動対応

**影響範囲**:
- views/equipment_form.py: フィールド定義更新
- views/hull_form.py: UI要素とデータ処理追加
- models/equipment_model.py: 確認済み（変更不要）
- models/hull_model.py: 確認済み（変更不要）

**期待効果**:
- 設計データの詳細記録が可能
- ユーザーの設計管理機能向上

---

### 🔧 StateParser日付トークン対応修正
**時刻**: 10:30
**概要**: StateParserで日付形式（例: 1938.3.12）のトークンが解析できない問題を修正

**問題**:
- `1938.3.12 = { add_claim_by = DEU }` のような日付形式がSyntaxErrorになる
- レクサーが日付パターンを認識できていない
- パーサー文法で日付トークンが定義されていない

**修正内容**:
- **DATE トークン追加**: `\d{4}\.\d{1,2}\.\d{1,2}` パターンで日付を認識
- **パーサー文法更新**: KEY, value, value_item にDATEトークンを追加
- **日付イベント処理**: 解析結果に`dated_events`セクションを追加
- **エラーハンドリング強化**: より詳細なコンテキスト情報を提供
- **value_list処理改善**: SPACE トークンの正しい処理ロジックを実装
- **raw文字列対応**: 正規表現パターンでSyntaxWarning回避

**技術詳細**:
- `t_DATE()`: PLYの優先順位を利用して数値より先に日付をマッチ
- `p_KEY()`: ID, NUMBER, DATE, QUALIFIED_ID を統一処理
- 日付キーの検出: `key.replace('.', '').isdigit()` で判定
- レクサーエラー位置のコンテキスト表示機能

**影響範囲**:
- parser/StateParser.py: レクサー・パーサー文法の大幅更新
- 全てのstateファイル解析処理（特に歴史イベント含む）

## 2025年6月11日 (水)

### 🔧 StateParser並列実行エラー修正
**時刻**: 18:00
**概要**: スレッドごとにパーサーとレクサーを生成し、並列解析時のSyntaxErrorを解消

**修正内容**:
- parser/StateParser.py: スレッドローカルなパーサーとレクサー生成関数を追加
- parser/StateParser.py: parseメソッドでスレッド専用インスタンスを使用

**影響範囲**:
- マルチスレッド環境でのstateファイル解析処理

### 🔧 Web検索機能：ICUエラー修正
**時刻**: 17:30  
**概要**: QWebEngineViewのICUデータファイルエラーを修正し、代替方式を実装

**修正内容**:
- **ICUエラー対応**: WebEngine利用可能性チェック機能追加
- **代替方式実装**: WebEngine失敗時はデスクトップブラウザ連携に自動切り替え
- **堅牢性向上**: WebEngineCore import エラーハンドリング強化
- **ユーザー通知**: ステータスバーで動作モードを明示
- **URLエンコーディング**: 検索クエリの適切なエンコーディング処理

**技術詳細**:
- WebEngine利用不可時はQTextBrowserで説明表示
- QDesktopServices.openUrl()でシステムブラウザ起動
- ナビゲーション機能は利用可能時のみ有効化

---

### ✅ Web検索機能実装
**時刻**: 17:15  
**概要**: 設計・登録系画面にWeb検索機能を統合実装

**実装内容**:
- **WebSearchWidget**: コンパクトなWeb検索ダイアログ
  - QWebEngineViewベースの軽量ブラウザ
  - 複数検索エンジン対応（Google, Wikipedia, Yahoo, Bing）
  - クイック検索ボタン（Wikipedia, 艦船, 兵器, 歴史, 技術）
  - ナビゲーション機能（戻る・進む・更新）
- **WebSearchButton**: 各画面埋め込み用の小さなボタン
- **動的検索クエリ**: 選択された艦種・装備タイプに応じて検索クエリを自動更新
- **Windows 98風デザイン**: 既存UIとの統一感

**影響範囲**:
- utils/web_search_widget.py: 新規作成
- views/design_view.py: Web検索ボタン追加、艦種連動検索
- views/equipment_form.py: Web検索ボタン追加、装備タイプ連動検索  
- views/hull_form.py: Web検索ボタン追加

**期待効果**:
- 設計作業中の調べ物が効率化
- 艦船・兵器の資料検索が迅速に
- ユーザーワークフローの改善

---

### ✅ 国家・国旗データ全MOD一括プリロード実装
**時刻**: 17:05  
**概要**: 初回起動時に全MOD分の国家・国旗データを一括でプリロードする機能を実装

**実装内容**:
- **自動MOD検索**: 設定済みMOD + 一般的なMODディレクトリを自動検索
- **バックグラウンドプリロード**: UI操作を妨げない非同期処理
- **スプライトシート生成**: 全MODの国旗を統合スプライトシートに変換
- **起動時自動実行**: アプリ起動2秒後に自動でプリロード開始
- **プリロード状態管理**: 重複実行防止と完了状態の管理

**影響範囲**:
- controllers/app_controller.py: プリロード機能追加
  - `start_nations_preload()`: プリロード開始処理
  - `_preload_all_nations_background()`: バックグラウンド処理
  - `_discover_available_mods()`: MOD自動検索
  - プリロード完了・エラー処理

**期待効果**:
- 2回目以降の国家リスト表示が瞬時に
- 全MODの国旗表示が高速化
- ユーザーの待機時間大幅削減

---

### ✅ 包括的キャッシュシステム実装
**時刻**: 16:45  
**概要**: プロジェクト全体のファイル読み込み処理にキャッシュシステムを実装

**実装内容**:
- **モデルレベルキャッシュ**: hull_model.py, equipment_model.pyにキャッシュ機能追加
- **データローダーキャッシュ**: utils/data_loaders.pyでCSV/YAML読み込みをキャッシュ化
- **パフォーマンス監視**: utils/performance_monitor.py新規作成
- **新キャッシュタイプ**: hulls_all, equipment_all, equipment_templates, csv_import, status_definitions

**影響範囲**:
- controllers/app_controller.py: キャッシュマネージャー統合
- models/: 全モデルファイルのキャッシュ対応
- utils/: データローダーとパフォーマンス監視追加

**期待効果**:
- 起動時間: 50-80%短縮
- データ読み込み: 2-50倍高速化
- ユーザー体験の大幅改善

---

### ✅ MOD設計データ永続キャッシュ実装
**時刻**: 16:20  
**概要**: MOD設計データの取得処理を永続キャッシュで最適化

**実装内容**:
- MODDataCacheManagerの統合
- get_nation_mod_designs()メソッドのキャッシュ対応
- タイムスタンプベース有効性チェック

**影響範囲**:
- controllers/app_controller.py: MODキャッシュマネージャー初期化
- utils/mod_data_cache_manager.py: 既存ファイル活用

**期待効果**:
- 2回目以降のMOD設計データ読み込みが瞬時に

---

### ✅ 国家リスト・国旗キャッシュシステム実装
**時刻**: 15:50  
**概要**: 国家リストと国旗表示をスプライトシート方式で最適化

**実装内容**:
- utils/flag_sprite_manager.py新規作成
- 複数の小さな国旗を1枚の大きなスプライトシートに統合
- 座標メタデータでの管理システム
- 32x20ピクセル統一サイズ処理

**影響範囲**:
- controllers/app_controller.py: get_nations()メソッド改修
- views/nation_view.py: スプライトシートからの国旗読み込み

**期待効果**:
- メモリ使用量削減
- 国家リスト表示の大幅高速化

---

### ✅ 永続キャッシュシステム基盤構築
**時刻**: 15:10  
**概要**: タイムスタンプベースの永続キャッシュシステム実装

**実装内容**:
- utils/cache_manager.py改修: メタデータ永続化機能
- タイムスタンプ比較によるキャッシュ有効性判定
- 複数ファイル依存対応
- 自動クリーンアップ機能

**影響範囲**:
- utils/maptest2.py: プロヴィンス中心座標キャッシュ対応
- controllers/app_controller.py: キャッシュシステム統合

**期待効果**:
- アプリケーション再起動後もキャッシュが有効
- 重い処理の実行回数大幅削減

---

### ✅ 重複処理防止・港湾移動機能修正
**時刻**: 14:30  
**概要**: 各種重複処理の修正とマップ移動機能の改善

**実装内容**:
- views/fleet_view.py: 重複初期化防止フラグ追加
- utils/maptest2.py: 港湾ボタンクリック時の座標移動修正
- 座標系変換とループ描画の整合性確保

**影響範囲**:
- プロヴィンス中心座標計算の重複実行解消
- マップビューの正確な中央移動

**期待効果**:
- 処理の重複実行による無駄な計算を排除
- ユーザーインターフェースの操作性向上

---

### ✅ エラー処理・コード品質向上
**時刻**: 14:00  
**概要**: 各種エラーの修正とコード品質の改善

**実装内容**:
- views/design_view.py: ゼロ除算エラー修正
- utils/sync_manager.py: SyntaxWarning修正（raw文字列化）
- main.py: macOS Qt platform plugin問題修正

**影響範囲**:
- エラーハンドリングの堅牢化
- クロスプラットフォーム対応強化

**期待効果**:
- アプリケーションの安定性向上
- エラー発生率の削減

---

### ✅ マップ描画処理軽量化
**時刻**: 13:30  
**概要**: マップビューの描画パフォーマンス最適化

**実装内容**:
- utils/maptest2.py: QGraphicsView最適化フラグ設定
- Pixmapキャッシュシステム実装
- アンチエイリアシング無効化
- views/nation_view.py: 国旗描画でFastTransformation使用

**影響範囲**:
- マップ描画の全体的なパフォーマンス向上
- メモリ使用量の最適化

**期待効果**:
- 描画処理の大幅高速化
- UI応答性の改善

---

## CLAUDE.mdルール追加履歴

### 2025-06-11 16:45
- **包括的キャッシュシステム**: モデルレベルキャッシュとデータローダーキャッシュの標準化
- **開発ログ管理ルール**: 作業記録の保持義務化

### 2025-06-11 16:20
- **MODデータ永続キャッシュ**: 専用キャッシュマネージャーの使用標準化

### 2025-06-11 15:50
- **画像アセット最適化**: スプライトシート統合とハッシュベース有効性の標準化

### 2025-06-11 15:10
- **キャッシュシステム設計**: タイムスタンプベース永続キャッシュの標準化

### 2025-06-11 14:30
- **重複処理の防止**: イベントハンドラーでの状態管理フラグ使用の標準化

### 2025-06-11 14:00
- **エラー処理**: ゼロ除算防止とraw文字列使用の標準化
- **Qt/PyQt5環境設定**: macOS環境での問題対処法の標準化

### 2025-06-11 13:30
- **パフォーマンス最適化ルール**: 描画処理軽量化の標準化