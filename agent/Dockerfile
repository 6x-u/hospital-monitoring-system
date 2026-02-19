FROM python:3.12-slim

LABEL maintainer="MERO:TG@QP4RM"
LABEL app="hms-agent"

WORKDIR /agent

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r agent && useradd -r -g agent -s /bin/false agent

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=agent:agent . .

USER agent

ENV AGENT_API_URL=""
ENV AGENT_API_KEY=""
ENV AGENT_HOST_ID=""
ENV AGENT_ENCRYPTION_KEY=""
ENV AGENT_COLLECTION_INTERVAL_SECONDS="30"

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import psutil; psutil.cpu_percent()" || exit 1

CMD ["python", "src/agent.py"]
