@echo off
chcp 65001 >nul
echo ========================================
echo 議事録メーカー - 起動中...
echo ========================================
echo.

REM 仮想環境の確認
if not exist venv\ (
    echo [ERROR] 仮想環境が見つかりません。
    echo 最初に setup.bat を実行してください。
    echo.
    pause
    exit /b 1
)

REM credentials.jsonの確認
if not exist credentials.json (
    echo [WARNING] credentials.jsonが見つかりません。
    echo APIキーを設定してください。
    echo.
    echo 手順：
    echo 1. credentials.jsonファイルを作成
    echo 2. 以下の内容を記述：
    echo {
    echo   "google_api_key": "YOUR_GOOGLE_API_KEY_HERE"
    echo }
    echo 3. Google AI Studio (https://aistudio.google.com/) でAPIキーを取得
    echo.
    
    REM credentials.jsonのテンプレートを作成（存在しない場合のみ）
    (
        echo {
        echo   "google_api_key": "YOUR_GOOGLE_API_KEY_HERE"
        echo }
    ) > credentials.json
    echo [INFO] credentials.jsonのテンプレートを作成しました。
    echo       ファイルを編集してAPIキーを入力してから再度実行してください。
    echo.
    pause
    exit /b 1
)

echo [INFO] 仮想環境をアクティベート中...
call venv\Scripts\activate.bat

echo [INFO] Streamlitアプリを起動中...
echo ブラウザが自動的に開きます...
echo 終了するには Ctrl+C を押してください。
echo.

streamlit run app.py

REM アプリ終了後
echo.
echo ========================================
echo アプリを終了しました。
echo ========================================
pause

