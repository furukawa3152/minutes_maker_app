import streamlit as st
import google.generativeai as genai
import time
import os
import json
import csv
from datetime import datetime
from pathlib import Path
from google.api_core import exceptions as google_exceptions

# ---------------------------------------------------------
# 設定
# ---------------------------------------------------------
# クレデンシャルファイルからAPIキーを読み込む
def load_credentials():
    """credentials.jsonからAPIキーを読み込む"""
    cred_file = Path("credentials.json")
    if cred_file.exists():
        with open(cred_file, "r") as f:
            credentials = json.load(f)
            return credentials.get("google_api_key", "")
    return ""

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

st.set_page_config(page_title="議事録メーカー", layout="wide")

st.title("🎙️ 議事録メーカー")
st.markdown("音声ファイルをアップロードすると、Geminiが内容を聴き取り、議事録を作成します。")

# クレデンシャルファイルからAPIキーを読み込み
default_api_key = load_credentials()

# サイドバーでAPIキー入力（クレデンシャルファイルの値をデフォルトとして使用）
if default_api_key:
    st.sidebar.success("✅ credentials.jsonからAPIキーを読み込みました")
    api_key = default_api_key
    # APIキーの一部を表示（セキュリティのため最初の4文字と最後の4文字のみ）
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    st.sidebar.text(f"APIキー: {masked_key}")
else:
    st.sidebar.warning("⚠️ credentials.jsonが見つかりません")
    st.sidebar.info("credentials.json.sampleを参考にcredentials.jsonを作成してください")
    api_key = st.sidebar.text_input("Google API Keyを入力", type="password")

# モデルはgemini-2.5-proに固定
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
uploaded_file = st.file_uploader("音声ファイルをアップロード (mp3, wav, m4a, mp4など)", type=["mp3", "wav", "m4a", "mp4", "aac", "flac"])

if uploaded_file is not None and st.button("議事録を作成する"):
    if not api_key:
        st.error("APIキーを入力してください。")
    else:
        genai.configure(api_key=api_key)
        
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

            # 2. Geminiにファイルをアップロード（リトライ機能付き）
            status_text.text("Geminiに音声を送信中... (これには時間がかかる場合があります)")
            max_retries = 3
            retry_count = 0
            audio_file = None
            
            while retry_count < max_retries:
                try:
                    audio_file = genai.upload_file(path=temp_filename)
                    break
                except (google_exceptions.ServiceUnavailable, Exception) as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 2 ** retry_count  # 指数バックオフ: 2秒, 4秒, 8秒
                        status_text.text(f"接続エラー。{wait_time}秒後にリトライします... ({retry_count}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        raise
            
            progress_bar.progress(40)

            # 3. ファイルの処理完了を待機
            # 音声が大きい場合、サーバー側で処理に時間がかかるためポーリングが必要
            while audio_file.state.name == "PROCESSING":
                status_text.text("Gemini側で音声を解析中...")
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)
            
            if audio_file.state.name == "FAILED":
                raise ValueError("音声処理に失敗しました。")

            progress_bar.progress(60)

            # 4. 議事録生成を実行（リトライ機能付き）
            status_text.text("議事録を執筆中...")
            model = genai.GenerativeModel(model_name=model_type)
            
            max_retries = 3
            retry_count = 0
            response = None
            
            while retry_count < max_retries:
                try:
                    response = model.generate_content(
                        [prompt_text, audio_file],
                        request_options={"timeout": 600} # 長い会議用にタイムアウトを延長
                    )
                    break
                except (google_exceptions.ServiceUnavailable, Exception) as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 2 ** retry_count  # 指数バックオフ: 2秒, 4秒, 8秒
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

            # クリーンアップ (Gemini上のファイル削除は必要に応じて行う)
            # genai.delete_file(audio_file.name)
            
            # ログ記録（成功）
            log_status = "成功"
            processing_time = time.time() - start_time
            log_usage(filename, filesize_mb, processing_time, log_status, "", minutes_file_path)

        except google_exceptions.ServiceUnavailable as e:
            error_message = f"ServiceUnavailable: {str(e)}"
            processing_time = time.time() - start_time
            log_usage(filename, filesize_mb, processing_time, log_status, error_message, "")
            
            st.error("❌ サービスが一時的に利用できません（DNS解決エラー）")
            st.warning("""
            **対処方法:**
            1. インターネット接続を確認してください
            2. DNSサーバーの設定を確認してください
            3. ファイアウォールやプロキシの設定を確認してください
            4. しばらく時間をおいてから再度お試しください
            """)
            st.error(f"詳細: {str(e)}")
        except google_exceptions.DeadlineExceeded as e:
            error_message = f"DeadlineExceeded: {str(e)}"
            processing_time = time.time() - start_time
            log_usage(filename, filesize_mb, processing_time, log_status, error_message, "")
            
            st.error("⏱️ リクエストがタイムアウトしました")
            st.warning("音声ファイルが大きい場合、処理に時間がかかることがあります。もう一度お試しください。")
        except google_exceptions.PermissionDenied as e:
            error_message = f"PermissionDenied: {str(e)}"
            processing_time = time.time() - start_time
            log_usage(filename, filesize_mb, processing_time, log_status, error_message, "")
            
            st.error("🔐 APIキーが無効です")
            st.warning("APIキーを確認してください。Google AI Studio (https://aistudio.google.com/) でAPIキーを取得できます。")
        except Exception as e:
            error_message = str(e)
            processing_time = time.time() - start_time
            log_usage(filename, filesize_mb, processing_time, log_status, error_message, "")
            
            error_msg = str(e)
            if "DNS" in error_msg or "DNS resolution" in error_msg:
                st.error("🌐 DNS解決エラーが発生しました")
                st.warning("""
                **対処方法:**
                1. インターネット接続を確認してください
                2. DNSサーバーの設定を確認してください（例: 8.8.8.8, 1.1.1.1）
                3. ファイアウォールやプロキシの設定を確認してください
                4. しばらく時間をおいてから再度お試しください
                """)
            else:
                st.error(f"❌ エラーが発生しました: {error_msg}")
            
            # デバッグ用（開発時のみ表示）
            if st.sidebar.checkbox("詳細なエラー情報を表示"):
                st.exception(e)