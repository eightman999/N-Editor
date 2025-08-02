# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NavalDesignSystem (NDS) is a Python desktop application built with PyQt5 for creating Hearts of Iron IV (HOI4) modifications. It provides a graphical interface for editing naval OOB files, ship designs, equipment, and other HOI4 game data.

## Technology Stack

- **Language**: Python 3.12+
- **GUI Framework**: PyQt5 (~5.15.11)
- **Package Management**: Poetry
- **Parsers**: PLY (Python Lex-Yacc) for HOI4 script parsing
- **Key Dependencies**: NumPy, Pillow, OpenCV, PyYAML, Requests

## Development Commands

### Installation and Setup
```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Run the application
python main.py
```

### Common Operations
- **Start Application**: `python main.py`
- **Add Dependencies**: `poetry add <package>`
- **Update Dependencies**: `poetry update`

## Architecture

### MVC Structure
- **Models** (`models/`): Data structures and business logic
- **Views** (`views/`): PyQt5 UI components and forms  
- **Controllers** (`controllers/`): Application logic coordination
- **Parsers** (`parser/`): PLY-based HOI4 script parsers
- **Utils** (`utils/`): Caching, performance monitoring, calculations

### Key Classes
- `AppController`: Central application coordinator with 70+ methods
- `EquipmentModel`/`HullModel`: Data management
- `NavalDesignSystem`: Main window implementation
- Various calculator classes for equipment statistics

## Code Style and Conventions

### Python Conventions
- **Classes**: PascalCase (`AppController`, `EquipmentModel`)
- **Methods/Variables**: snake_case (`load_equipment`, `current_mod`)
- **Constants**: UPPER_CASE (`VERSION_FILE`, `BASE_ARMOR_VALUE_COEF`)
- **Strings**: Use raw strings (`r""`) for regex and paths to avoid SyntaxWarning

### PyQt5 Patterns
- Extensive use of signals/slots for component communication
- Background operations via QThreadPool
- Custom Windows 95-style CSS styling
- MVC separation with clear responsibilities

### Error Handling
- Always check for zero division: `value/divisor if divisor != 0 else 0`
- Comprehensive logging with rotating file handlers
- Graceful degradation on errors with user feedback

## Performance Guidelines

### Caching System
- Implement aggressive caching with timestamp-based invalidation
- Use `CacheManager` for file-based operations
- Cache heavy operations like image processing and data parsing
- Check file modification times before using cached data

### UI Optimization
- Set QGraphicsView optimization flags:
  ```python
  view.setOptimizationFlag(QGraphicsView.DontSavePainterState, True)
  view.setOptimizationFlag(QGraphicsView.DontAdjustForAntialiasing, True)
  view.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)
  ```
- Disable antialiasing for performance: `QPainter.Antialiasing, False`
- Use `Qt.FastTransformation` for image scaling
- Implement sprite sheets for multiple small images

### Threading
- Use QThreadPool for background file I/O and parsing
- Implement worker classes with proper signal-based communication
- Prevent duplicate processing with state management flags

## File and Data Handling

### Supported Formats
- **HOI4 Scripts**: Custom PLY parsers for `.txt` files
- **Configuration**: YAML and JSON for settings
- **Data Storage**: File-based with extensive caching
- **Images**: PNG/BMP processing with optimization

### Parser Architecture
- Separate parsers for different HOI4 file types
- Thread-safe parsing with proper error handling
- Caching of parsed results with metadata tracking

## Testing and Debugging

### Current Testing Approach
- Manual testing through GUI interface
- Built-in debug menu with cache functionality tests
- Performance monitoring utilities in `utils/`
- No automated test framework currently in use

### Debug Features
- Cache functionality testing via debug menu
- Conflict resolution dialog testing
- Performance benchmarking for heavy operations
- Detailed logging for troubleshooting

## Git Integration

The application includes GitHub synchronization features for team collaboration:
- Automatic data synchronization with remote repositories
- Conflict resolution dialogs for merge conflicts
- Background sync operations with progress tracking

## Platform Considerations

### Cross-Platform Support
- Platform-specific Qt plugin path handling
- macOS-specific environment variable settings
- Windows-style UI theming across all platforms
- Proper virtual environment detection and setup

## 🔨 最重要ルール - 新しいルールの追加プロセス

ユーザーから今回限りではなく常に対応が必要だと思われる指示を受けた場合：

1. 「これを標準のルールにしますか？」と質問する
2. YESの回答を得た場合、CLAUDE.mdに追加ルールとして記載する
3. 以降は標準ルールとして常に適用する

このプロセスにより、プロジェクトのルールを継続的に改善していきます。

## Gemini CLI 連携ガイド

### 目的
ユーザーが **「Geminiと相談しながら進めて」** （または同義語）と指示した場合、Claude は以降のタスクを **Gemini CLI** と協調しながら進める。
Gemini から得た回答はそのまま提示し、Claude 自身の解説・統合も付け加えることで、両エージェントの知見を融合する。

---

### トリガー
- 正規表現: `/Gemini.*相談しながら/`
- 例:
- 「Geminiと相談しながら進めて」
- 「この件、Geminiと話しつつやりましょう」

---

### 基本フロー
1. **PROMPT 生成**
Claude はユーザーの要件を 1 つのテキストにまとめ、環境変数 `$PROMPT` に格納する。

2. **Gemini CLI 呼び出し**
```bash
gemini <<EOF
$PROMPT
EOF```

## 🚀 パフォーマンス最適化ルール

### 描画処理の軽量化
- QGraphicsViewには最適化フラグを設定：
  - `setOptimizationFlag(QGraphicsView.DontSavePainterState, True)`
  - `setOptimizationFlag(QGraphicsView.DontAdjustForAntialiasing, True)`
  - `setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)`
- 描画処理にはキャッシュシステムを実装
- アンチエイリアシングは原則無効化（`QPainter.Antialiasing, False`）
- 画像スケーリングには`Qt.FastTransformation`を使用
- 大きなメソッドは機能別に分離してキャッシュ効率を向上

## 🔧 コード品質ルール

### Python文字列とエスケープシーケンス
- 正規表現やパス文字列にはraw文字列（`r"""`）を使用
- バックスラッシュを含む文字列リテラルでSyntaxWarningが出る場合は必ずraw文字列に変換

### Qt/PyQt5環境設定
- macOS環境でのQt platform plugin問題に対処：
  - 複数のプラグインパスを検索して設定
  - `QT_QPA_PLATFORM=cocoa`を明示的に設定
  - システムパスの干渉を避けるため適切な環境変数管理を実装

### エラー処理
- ゼロ除算の防止：
  - 除算前に分母が0でないことを必ず確認
  - `value/divisor` → `value/divisor if divisor != 0 else 0` または適切なデフォルト値
  - 特に割合計算では分母の値をチェック

### 重複処理の防止
- イベントハンドラーでの重複実行を防止：
  - 状態管理フラグを使用して既に処理済みかをチェック
  - 重い処理（マップデータ読み込み、計算処理等）は特に注意
  - シグナル連鎖による意図しない重複実行を防ぐ
- 初期化処理の最適化：
  - `_initialized`、`_current_data`等のフラグで状態を管理
  - 同じデータでの再初期化を避ける

### キャッシュシステム設計
- タイムスタンプベース永続キャッシュの実装：
  - 元ファイルの更新時間をメタデータとして保存
  - 起動時にファイルタイムスタンプを比較してキャッシュ有効性を判断
  - 複数ファイル依存（例: `file1.bmp+file2.csv`）のキャッシュに対応
- メタデータ管理：
  - `_cache_metadata.json`でキャッシュ詳細情報を永続化
  - 無効なメタデータの自動クリーンアップ機能
  - キャッシュ使用状況の詳細ログ出力
- 画像アセット最適化：
  - **スプライトシート統合**: 複数の小さな画像を1枚の大きな画像に統合
  - **座標メタデータ管理**: 各画像の切り出し座標をJSONで保存
  - **統一サイズ処理**: アイコンサイズを統一して配置効率を最大化
  - **ハッシュベース有効性**: 画像内容の変更検出でキャッシュ無効化
- MODデータ永続キャッシュ：
  - **専用キャッシュマネージャー**: MODDataCacheManagerでデータタイプ別管理
  - **複数ディレクトリ監視**: common/配下の関連ディレクトリを一括監視
  - **元ファイル更新検出**: タイムスタンプ比較でキャッシュ有効性を判断
  - **パフォーマンス測定**: 読み込み時間とキャッシュ効果の詳細ログ出力
- 包括的キャッシュシステム：
  - **モデルレベルキャッシュ**: 全モデルでファイル読み込み処理をキャッシュ化
  - **データローダーキャッシュ**: CSV、YAML、JSON等の読み込み結果を永続化
  - **パフォーマンス監視**: 実行時間測定とキャッシュ効果の自動検証
  - **統合キャッシュ管理**: モデル間でのキャッシュマネージャー共有

## 📋 開発ログ管理ルール

### 作業記録の保持
- 実装した機能や修正内容は`DEVELOPMENT_LOG.md`に日付込みで記録
- 各作業には日時、概要、実装内容、影響範囲を明記
- パフォーマンス改善の場合は改善効果も記録
- **作業後は必ずDEVELOPMENT_LOG.mdに記録すること**
- **作業後は必ずコミットすること**

### 時刻表記ルール
- `DEVELOPMENT_LOG.md`およびその他のドキュメントファイルの時刻は**JPN標準時（JST）**を採用
- 時刻表記形式：`HH:MM`（24時間制）
- タイムゾーン表記は省略（JST前提）
- 例：`**時刻**: 14:30`、`**時刻**: 09:15`