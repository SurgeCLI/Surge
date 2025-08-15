FROM python:3-slim-buster

WORKDIR /app

COPY cli/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY cli /app/cli

ENTRYPOINT ["python", "cli/app.py"]

CMD [""]