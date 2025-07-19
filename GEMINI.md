# Gemini CLI 連携ガイド

## 目的
ユーザーから「Geminiと相談しながら進めて」などの指示があった場合、Gemini CLI を使って回答を取得し、Claude の解説を加えて提示します。

## トリガー
- 正規表現: `/Gemini.*相談しながら/`
- 例:
  - "Geminiと相談しながら進めて"
  - "この件、Geminiと話しつつやりましょう"

## 基本フロー
1. **PROMPT生成**
   - ユーザー要望をまとめ、環境変数 `$PROMPT` に格納。
2. **Gemini CLI呼び出し**
   ```bash
   gemini <<EOF
   $PROMPT
   EOF
   ```
3. **結果提示**
   - Gemini の出力をそのまま提示し、必要に応じてClaudeが補足説明を行う。

## 開発ログへの記録
Gemini CLI を使用した作業内容は `DEVELOPMENT_LOG.md` に時刻(24時間制、JST)付きで記録してください。
