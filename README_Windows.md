# 議事録メーカー - Windows版セットアップガイド

Windows環境での議事録メーカーのセットアップと使用方法を説明します。

## 前提条件

- Python 3.8以上がインストールされていること
- インターネット接続

Pythonのバージョン確認：
```cmd
python --version
```

## 初回セットアップ

### 方法1: バッチファイルで自動セットアップ（推奨）

1. `setup.bat` をダブルクリックまたはコマンドプロンプトから実行

```cmd
setup.bat
```

2. セットアップが完了したら、`credentials.json` を編集してGoogle API Keyを設定

```json
{
  "google_api_key": "YOUR_GOOGLE_API_KEY_HERE"
}
```

Google API Keyは [Google AI Studio](https://aistudio.google.com/) で取得できます。

### 方法2: 手動セットアップ

```cmd
# 1. 仮想環境の作成
python -m venv venv

# 2. 仮想環境のアクティベート
venv\Scripts\activate.bat

# 3. 必要なパッケージのインストール
pip install -r requirements.txt

# 4. credentials.jsonの作成
echo {"google_api_key": "YOUR_API_KEY"} > credentials.json
```

## アプリの起動

### 方法1: バッチファイルで起動（推奨）

`run.bat` をダブルクリックまたはコマンドプロンプトから実行

```cmd
run.bat
```

### 方法2: 手動で起動

```cmd
# 仮想環境のアクティベート
venv\Scripts\activate.bat

# Streamlitアプリの起動
streamlit run app.py
```

ブラウザで `http://localhost:8501` が自動的に開きます。

## アプリの停止

- バッチファイルから起動した場合: `Ctrl+C` を押してからウィンドウを閉じる
- コマンドプロンプトから起動した場合: `Ctrl+C` を押す

## トラブルシューティング

### Pythonが見つからない

```
'python' は、内部コマンドまたは外部コマンド、
操作可能なプログラムまたはバッチ ファイルとして認識されていません。
```

**解決方法:**
1. Pythonが正しくインストールされているか確認
2. Pythonをシステム環境変数PATHに追加
3. `py` コマンドを試す（`py -m venv venv`）

### パッケージのインストールエラー

**解決方法:**
```cmd
# pipをアップグレード
python -m pip install --upgrade pip

# 再度インストール
pip install -r requirements.txt
```

### DNS解決エラーが発生する場合

**解決方法:**
1. インターネット接続を確認
2. DNSサーバーの設定を確認
   - Google DNS: 8.8.8.8
   - Cloudflare DNS: 1.1.1.1
3. ファイアウォールの設定を確認
4. プロキシを使用している場合は設定を確認

### 文字化けする場合

バッチファイルは UTF-8 エンコーディングで保存してください。
エディタで開いて保存形式を確認してください。

## ファイル構成

```
minutes_maker_app/
├── setup.bat              # 初回セットアップ用バッチファイル
├── run.bat                # アプリ起動用バッチファイル
├── app.py                 # メインアプリケーション
├── requirements.txt       # 必要なPythonパッケージ
├── credentials.json       # APIキー設定（要作成）
├── .gitignore            # Git管理から除外するファイル
├── README.md             # 一般的なREADME
├── README_Windows.md     # Windows版README（このファイル）
├── venv/                 # 仮想環境（setup.batで自動作成）
└── logs/                 # 使用ログ（自動作成）
    └── usage_log.csv
```

## 使い方

1. `run.bat` を実行
2. ブラウザが開いたら音声ファイルをアップロード
3. 必要に応じてプロンプトをカスタマイズ
4. 「議事録を作成する」ボタンをクリック
5. 生成された議事録をダウンロード

## ログの確認

使用履歴は `logs\usage_log.csv` に自動保存されます。
Excelやメモ帳で開いて確認できます。

## サポート

問題が発生した場合は、以下を確認してください：
- Pythonのバージョン（3.8以上）
- インターネット接続
- credentials.jsonの設定
- ログファイル（logs\usage_log.csv）のエラーメッセージ

