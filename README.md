# 議事録メーカー

音声ファイルをアップロードすると、Google Gemini 2.5 Proが内容を聴き取り、議事録を自動作成するStreamlitアプリです。

## 機能

- 🎙️ 音声ファイル（mp3, wav, m4a, mp4, aac, flac）から議事録を自動生成
- ⚙️ プロンプトのカスタマイズが可能
- 📊 使用ログをCSV形式で自動保存
- 🔄 接続エラー時の自動リトライ機能
- 📥 議事録のMarkdown形式でのダウンロード

## セットアップ

### 1. 必要なパッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. APIキーの設定

1. `credentials.json.sample` をコピーして `credentials.json` を作成

```bash
cp credentials.json.sample credentials.json
```

2. `credentials.json` を編集してGoogle API Keyを入力

```json
{
  "google_api_key": "YOUR_GOOGLE_API_KEY_HERE"
}
```

Google API Keyは [Google AI Studio](https://aistudio.google.com/) で取得できます。

### 3. アプリの起動

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501` が自動的に開きます。

## 使い方

1. 音声ファイルをアップロード
2. 必要に応じてプロンプトをカスタマイズ（サイドバー）
3. 「議事録を作成する」ボタンをクリック
4. 生成された議事録をダウンロード

## ログ

使用履歴は `logs/usage_log.csv` に自動保存されます。

ログには以下の情報が記録されます：
- 実行日時
- ファイル名
- ファイルサイズ（MB）
- 処理時間（秒）
- ステータス（成功/失敗）
- エラーメッセージ（失敗時）

## 注意事項

- `credentials.json` はGitにコミットしないでください（.gitignoreに含まれています）
- 大きな音声ファイルは処理に時間がかかる場合があります
- Google Gemini APIの利用には料金が発生する場合があります

## トラブルシューティング

### DNS解決エラーが発生する場合

DNSサーバーの設定を変更してください：

```bash
# Google DNSとCloudflare DNSを設定
networksetup -setdnsservers Wi-Fi 8.8.8.8 1.1.1.1

# DNSキャッシュをクリア
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder
```

### APIキーエラーが発生する場合

1. `credentials.json` のAPIキーが正しいか確認
2. Google AI Studioで新しいAPIキーを取得
3. APIキーの権限が有効か確認

## ライセンス

MIT License

