# API image. Built on Ubuntu so the scientific stack comes from apt, which ships
# prebuilt packages for s390x (IBM LinuxONE) as well as x86_64/arm64. No compiling.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-numpy python3-pandas python3-scipy python3-sklearn python3-joblib \
      python3-fastapi python3-uvicorn python3-pydantic \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY src ./src
COPY scripts ./scripts
RUN mkdir -p data/synthetic models
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s \
  CMD python3 -c "import urllib.request as u; u.urlopen('http://localhost:8000/health')" || exit 1
# First start generates data and trains the model (~30s) if they are missing.
CMD ["sh", "-c", "python3 -m src.bootstrap && exec python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"]
