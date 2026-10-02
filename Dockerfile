FROM python:3.14-slim
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir . && rm -rf /src
WORKDIR /
USER nobody
EXPOSE 9811
CMD ["xiaomi-air-purifier-exporter"]
