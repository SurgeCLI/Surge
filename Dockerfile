FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping traceroute mtr-tiny curl dnsutils iproute2 htop iotop iftop net-tools sysstat procps coreutils grep sed gawk wget && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY cli ./cli
COPY ai ./ai
COPY config ./config
COPY pyproject.toml .

RUN pip install --no-cache-dir .

ENV PYTHONPATH="/app"

ENTRYPOINT ["surge"]
CMD ["--help"]