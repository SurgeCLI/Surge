FROM python:3-slim-bullseye

RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping traceroute mtr-tiny curl dnsutils iproute2 htop iotop iftop net-tools sysstat procps coreutils grep sed gawk wget && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY cli/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pytest

COPY . /app

ENTRYPOINT ["python", "-m", "cli.app"]
CMD [""]
