FROM python:3-slim-bullseye

RUN apt-get update && apt-get install -y htop iotop iftop net-tools sysstat procps coreutils grep sed gawk curl wget && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY cli/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY cli /app/cli

ENTRYPOINT ["python", "cli/app.py"]

CMD [""]
