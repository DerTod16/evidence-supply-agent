FROM python:3.13-slim
WORKDIR /app

# 先装依赖（利用缓存层）
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# 再拷代码
COPY apps/api ./apps/api
COPY apps/web ./apps/web
COPY examples ./examples

ENV LLM_MODE=demo \
    LLM_BASE_URL=https://api.deepseek.com/v1 \
    LLM_MODEL=deepseek-chat

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "apps/api", "--host", "0.0.0.0", "--port", "8000"]
