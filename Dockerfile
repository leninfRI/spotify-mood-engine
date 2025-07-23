# 使用官方的 Python 映像檔
FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 複製依賴清單並安裝
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# 複製您的後端程式碼
COPY ./spotify_backend.py /app/spotify_backend.py

# 設定環境變數，讓 Uvicorn 在 Railway 指定的端口上運行
ENV PORT 8080
EXPOSE 8080

# 設定容器啟動時要執行的指令
CMD ["uvicorn", "spotify_backend:app", "--host", "0.0.0.0", "--port", "8080"]
