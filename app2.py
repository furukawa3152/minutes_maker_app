import streamlit as st
import time
import os
import json
import csv
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types, errors as genai_errors

# ---------------------------------------------------------
# 設定
# ---------------------------------------------------------
# クレデンシャルファイルから Vertex AI の設定を読み込む
def load_credentials():
    """
    credentials.json から Vertex AI 用の設定を読み込みます。

    例：
    {
        "project_id": "your-gcp-project-id",
        "location": "asia-northeast1"
    }
    """
    cred_file = Path("credentials.json")
    if cred_file.exists():
        with open(cred_file, "r", encoding="utf-8") as f:
            credentials = json.load(f)
            project_id = credentials.get("project_id", "")
            location = credentials.get("location", "")
            return project_id, location
    return "", ""

# ログファイルのパス
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "usage_log.csv"
MINUTES_DIR = LOG_DIR / "minutes"

def init_log_file():
    """ログファイルを初期化（存在しない場合はヘッダーを作成、既存の場合はヘッダーを更新）"""
    LOG_DIR.mkdir(exist_ok=True)
    MINUTES_DIR.mkdir(exist_ok=True)
    
    expected_headers = [
        "実行日時", "ファイル名", "ファイルサイズ(MB)", 
        "処理時間(秒)", "ステータス", "エラーメッセージ", "議事録ファイル"
    ]
    
    if not LOG_FILE.exists():
        # 新規作成
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(expected_headers)
    else:
        # 既存ファイルのヘッダーを確認
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                if headers != expected_headers:
                    # ヘッダーが異なる場合、既存データを読み込んで新しい形式で書き直す
                    rows = list(reader)
                    # バックアップを作成
                    backup_file = LOG_FILE.with_suffix('.csv.backup')
                    import shutil
                    shutil.copy2(LOG_FILE, backup_file)
                    
                    # 新しい形式で書き直す
                    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(expected_headers)
                        # 既存のデータを書き直す（議事録ファイル列は空）
                        for row in rows:
                            # 既存の列数に応じて調整
                            while len(row) < len(expected_headers) - 1:
                                row.append("")
                            row.append("")  # 議事録ファイル列を追加
                            writer.writerow(row)
        except Exception:
            # エラーが発生した場合は新規作成
            pass

def save_minutes(minutes_text, original_filename):
    """議事録をファイルに保存し、ファイルパスを返す"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # ファイル名から拡張子を除いた部分を取得
        base_name = Path(original_filename).stem
        # ファイル名に使用できない文字を置換
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in base_name)
        minutes_filename = f"{timestamp}_{safe_name}.md"
        minutes_path = MINUTES_DIR / minutes_filename
        
        with open(minutes_path, "w", encoding="utf-8") as f:
            f.write(minutes_text)
        
        return str(minutes_path)
    except Exception as e:
        st.warning(f"議事録の保存に失敗しました: {e}")
        return ""

def log_usage(filename, filesize_mb, processing_time, status, error_msg="", minutes_file=""):
    """使用ログをCSVに記録"""
    try:
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                filename,
                f"{filesize_mb:.2f}",
                f"{processing_time:.2f}",
                status,
                error_msg,
                minutes_file
            ])
    except Exception as e:
        st.warning(f"ログの記録に失敗しました: {e}")

# ログファイルの初期化
init_log_file()

st.set_page_config(page_title="議事録メーカー（Vertex AI版）", layout="wide")

st.title("🎙️ 議事録メーカー（Vertex AI / Gemini 2.5 Pro）")
st.markdown("音声ファイルをアップロードすると、Vertex AI 上の Gemini が内容を聴き取り、議事録を作成します。")

# クレデンシャルファイルから Vertex の設定を読み込み
default_project_id, default_location = load_credentials()

# サイドバーで Vertex AI 設定入力
st.sidebar.header("Vertex AI 設定")

if default_project_id and default_location:
    st.sidebar.success("✅ credentials.json から Vertex の設定を読み込みました")
    project_id = default_project_id
    location = default_location
    st.sidebar.text(f"Project ID: {project_id}")
    st.sidebar.text(f"Location : {location}")
else:
    st.sidebar.warning("⚠️ credentials.json が見つからないか、project_id/location が未設定です。")
    st.sidebar.info("credentials.json に project_id と location を設定するか、下で直接入力してください。")
    project_id = st.sidebar.text_input("GCP Project ID", value="")
    location = st.sidebar.text_input("Location（例: asia-northeast1）", value="asia-northeast1")

# モデルは gemini-2.5-pro に固定（Vertex AI 上のモデル名）
model_type = "gemini-2.5-pro"

# プロンプトのカスタマイズ
default_prompt = """
あなたはプロの書記です。アップロードされた音声ファイルを聞き取り、以下のフォーマットで議事録を作成してください。

# 議事録

## 1. 会議の概要
*   **日時/場所**: （音声から推測できる場合のみ記載、不明なら「不明」）
*   **主要テーマ**:

## 2. 決定事項
*   
*   

## 3. 議論の詳細（トピック別）
*   **[トピック名]**: 
    *   内容詳細...

## 4. ネクストアクション（ToDo）
*   [担当者名]: [タスク内容] （期限: 〇月〇日）

## 注意点
*   「えー」「あー」などのフィラーは削除してください。
*   話者が特定できる場合は「Aさん」「Bさん」のように書き分けてください。
"""

prompt_text = st.sidebar.text_area("指示プロンプト（カスタマイズ可能）", default_prompt, height=300)

# ファイルアップロード
uploaded_file = st.file_uploader(
    "音声ファイルをアップロード (mp3, wav, m4a, mp4 など)",
    type=["mp3", "wav", "m4a", "mp4", "aac", "flac"]
)

if uploaded_file is not None and st.button("議事録を作成する"):
    if not project_id or not location:
        st.error("Vertex AI を利用するには Project ID と Location が必要です。サイドバーで設定してください。")
    else:
        # Vertex AI (Gemini in Vertex) 用のクライアントを作成
        # タイムアウトは 600 秒（ミリ秒指定）
        http_options = types.HttpOptions(timeout=600_000)
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
            http_options=http_options,
        )
        
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        # ログ用の変数を初期化
        start_time = time.time()
        filesize_mb = len(uploaded_file.getbuffer()) / (1024 * 1024)
        filename = uploaded_file.name
        log_status = "失敗"
        error_message = ""

        try:
            # 1. 一時ファイルとして保存
            status_text.text("ファイルを処理中...")
            temp_filename = "temp_audio_file" + os.path.splitext(uploaded_file.name)[1]
            with open(temp_filename, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            progress_bar.progress(20)

            # 2. Files API でアップロード（リトライ付き）
            status_text.text("Vertex AI に音声をアップロード中... (これには時間がかかる場合があります)")
            max_retries = 3
            retry_count = 0
            audio_file = None
            
            while retry_count < max_retries:
                try:
                    audio_file = client.files.upload(file=temp_filename)
                    break
                except genai_errors.APIError as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 2 ** retry_count  # 2秒, 4秒, 8秒
                        status_text.text(f"接続エラー。{wait_time}秒後にリトライします... ({retry_count}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        raise
            
            progress_bar.progress(40)

            # 3. ファイルの処理完了を待機（Files API の state をポーリング）
            while getattr(audio_file, "state", None) and getattr(audio_file.state, "name", "") == "PROCESSING":
                status_text.text("Vertex AI 側で音声を解析中...")
                time.sleep(2)
                audio_file = client.files.get(name=audio_file.name)
            
            if getattr(audio_file, "state", None) and audio_file.state.name == "FAILED":
                raise ValueError("音声処理に失敗しました。")

            progress_bar.progress(60)

            # 4. 議事録生成を実行（リトライ付き）
            status_text.text("議事録を執筆中...")
            
            max_retries = 3
            retry_count = 0
            response = None
            
            while retry_count < max_retries:
                try:
                    response = client.models.generate_content(
                        model=model_type,
                        contents=[prompt_text, audio_file],
                        # 追加の設定が必要なら config=types.GenerateContentConfig(...) を渡す
                    )
                    break
                except genai_errors.APIError as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 2 ** retry_count
                        status_text.text(f"接続エラー。{wait_time}秒後にリトライします... ({retry_count}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        raise

            progress_bar.progress(100)
            status_text.text("完了！")

            # 5. 議事録をファイルに保存
            minutes_file_path = save_minutes(response.text, filename)

            # 6. 結果表示
            st.subheader("📝 作成された議事録")
            st.markdown(response.text)

            # ダウンロードボタン
            st.download_button(
                label="テキストファイルとしてダウンロード",
                data=response.text,
                file_name="minutes.md",
                mime="text/markdown"
            )
            
            # ログ記録（成功）
            log_status = "成功"
            processing_time = time.time() - start_time
            log_usage(filename, filesize_mb, processing_time, log_status, "", minutes_file_path)

        except genai_errors.APIError as e:
            error_message = str(e)
            processing_time = time.time() - start_time
            log_usage(filename, filesize_mb, processing_time, log_status, error_message, "")
            
            code = getattr(e, "code", None)

            if code == 503:
                st.error("❌ サービスが一時的に利用できません")
                st.warning("""
**対処方法:**
1. インターネット接続を確認してください
2. GCP 側のステータスページを確認してください
3. しばらく時間をおいてから再度お試しください
""")
                st.error(f"詳細: {error_message}")
            elif code in (408, 504):
                st.error("⏱️ リクエストがタイムアウトしました")
                st.warning("音声ファイルが大きい場合、処理に時間がかかることがあります。もう一度お試しください。")
            elif code in (401, 403):
                st.error("🔐 権限エラーが発生しました")
                st.warning("Vertex AI の API 権限・認証情報を確認してください。")
            else:
                # DNSなど文字列で判定
                if "DNS" in error_message or "DNS resolution" in error_message:
                    st.error("🌐 DNS解決エラーが発生しました")
                    st.warning("""
**対処方法:**
1. インターネット接続を確認してください
2. DNSサーバーの設定を確認してください（例: 8.8.8.8, 1.1.1.1）
3. ファイアウォールやプロキシの設定を確認してください
4. しばらく時間をおいてから再度お試しください
""")
                else:
                    st.error(f"❌ エラーが発生しました: {error_message}")

        except Exception as e:
            error_message = str(e)
            processing_time = time.time() - start_time
            log_usage(filename, filesize_mb, processing_time, log_status, error_message, "")
            
            if "DNS" in error_message or "DNS resolution" in error_message:
                st.error("🌐 DNS解決エラーが発生しました")
                st.warning("""
**対処方法:**
1. インターネット接続を確認してください
2. DNSサーバーの設定を確認してください（例: 8.8.8.8, 1.1.1.1）
3. ファイアウォールやプロキシの設定を確認してください
4. しばらく時間をおいてから再度お試しください
""")
            else:
                st.error(f"❌ エラーが発生しました: {error_message}")

            # デバッグ用（開発時のみ表示）
            if st.sidebar.checkbox("詳細なエラー情報を表示"):
                st.exception(e)
