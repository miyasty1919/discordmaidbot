# 1. Pythonの実行環境（スリム版）を使用
FROM python:3.11-slim

# 2. 外部ライブラリ（yt-dlp用）に必要なシステムパッケージをインストール
# yt-dlpが正常に動作するために ffmpeg が必要な場合が多いため追加しています
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. コンテナ内の作業ディレクトリを /app に設定
WORKDIR /app

# 4. ローカルの app フォルダの中身をコンテナの /app にコピー
COPY app/ .

# 5. ライブラリのインストール
# --no-cache-dir をつけることでイメージサイズを軽量化します
RUN pip install --no-cache-dir -r requirements.txt

# 6. Koyebの死活監視（Health Check）をパスするためのポート開放設定
# main.pyにHTTPサーバー機能がない場合でも、Koyeb側でこのポートを指定します
EXPOSE 8000

# 7. Botの起動コマンド
CMD ["python", "main.py"]