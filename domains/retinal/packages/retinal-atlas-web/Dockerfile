FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps . && useradd --uid 10001 --create-home atlas
USER atlas
ENV PYTHONDONTWRITEBYTECODE=1 \
    RETINAL_ATLAS_HOST=0.0.0.0 \
    RETINAL_ATLAS_PORT=8877 \
    RETINAL_ATLAS_IMAGE_ROOT=/data/retinal_concept_reference_images
EXPOSE 8877
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8877/health', timeout=3)"
CMD ["python", "-m", "retinal_atlas_web"]
