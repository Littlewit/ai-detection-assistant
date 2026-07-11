FROM python:3.13-slim

WORKDIR /app

# 安装系统依赖（matplotlib 中文字体支持）
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data/uploads data/chroma_db data/reports data/standards

EXPOSE 8888

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8888", "--workers", "1"]
