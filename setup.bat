@echo off
chcp 65001 >nul
echo ========================================
echo 議事録メーカー - 初回セットアップ
echo ========================================
echo.

REM 仮想環境の確認
if exist venv\ (
    echo [INFO] 仮想環境が既に存在します。
) else (
    echo [INFO] 仮想環境を作成中...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] 仮想環境の作成に失敗しました。
        echo Pythonがインストールされているか確認してください。
        pause
        exit /b 1
    )
    echo [SUCCESS] 仮想環境を作成しました。
)

echo.
echo [INFO] 仮想環境をアクティベート中...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] 仮想環境のアクティベートに失敗しました。
    pause
    exit /b 1
)

echo.
echo [INFO] pipをアップグレード中...
python -m pip install --upgrade pip

echo.
echo [INFO] 必要なパッケージをインストール中...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] パッケージのインストールに失敗しました。
    pause
    exit /b 1
)

echo.
echo [INFO] credentials.jsonの確認...
if exist credentials.json (
    echo [SUCCESS] credentials.jsonが見つかりました。
) else (
    echo [WARNING] credentials.jsonが見つかりません。
    echo.
    echo 次の手順でAPIキーを設定してください：
    echo 1. credentials.jsonファイルを作成
    echo 2. 以下の内容を記述：
    echo {
    echo   "google_api_key": "YOUR_GOOGLE_API_KEY_HERE"
    echo }
    echo 3. Google AI Studio (https://aistudio.google.com/) でAPIキーを取得
    echo.
    
    REM credentials.jsonのテンプレートを作成
    (
        echo {
        echo   "google_api_key": "YOUR_GOOGLE_API_KEY_HERE"
        echo }
    ) > credentials.json
    echo [INFO] credentials.jsonのテンプレートを作成しました。
    echo       ファイルを編集してAPIキーを入力してください。
)

echo.
echo ========================================
echo セットアップが完了しました！
echo ========================================
echo.
echo 次回からは run.bat を実行してアプリを起動できます。
echo.
pause

