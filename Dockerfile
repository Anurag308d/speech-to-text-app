# Works on Hugging Face Spaces (Docker SDK) and any Docker host.
FROM python:3.12-slim

# Hugging Face Spaces runs containers as uid 1000.
RUN useradd -m -u 1000 user
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

# Bake the Piper voices into the image so the first Play click is instant.
RUN mkdir -p voices \
 && python -m piper.download_voices --download-dir voices en_US-lessac-medium hi_IN-pratham-medium \
 && chown -R user:user /app

USER user
ENV PORT=7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
