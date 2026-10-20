# CLAUDE.md

このファイルは、本リポジトリで作業する Claude Code 向けのガイドです。

## プロジェクト概要

Python による業務・作業の自動化スクリプトを管理するプロジェクトです。

## 開発環境

- 言語: Python 3.x
- 仮想環境: プロジェクト直下の `.venv` を使用する
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```
- 依存パッケージを追加したら `requirements.txt` を更新する
- OS は Windows（PowerShell）を前提とする

## コーディング規約

- PEP 8 に従う
- 関数・クラスには型ヒントを付ける
- ファイルパスは `pathlib.Path` で扱い、パスのハードコードは避ける
- パスワードや API キーなどの機密情報はコードに書かず、`.env` などで管理し、Git に含めない
- 1 スクリプト 1 目的を基本とし、共通処理はモジュールに切り出す

## Git 運用ルール

- **コードを変更するたびに、コミットして GitHub にプッシュする**
  ```powershell
  git add <変更したファイル>
  git commit -m "変更内容の要約"
  git push
  ```
- コミットメッセージは変更内容が分かるよう簡潔に書く（日本語可）
- 1 コミットには関連する変更のみを含める
- `.env`、`.venv/`、`__pycache__/` などは `.gitignore` に追加し、コミットしない
- プッシュ前に動作確認（スクリプトの実行やテスト）を行う
- `git push --force` など履歴を書き換える操作は行わない
