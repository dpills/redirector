FROM python:3.9-slim-buster

RUN apt update \
    && apt install -y redis-server

COPY ./requirements.txt /requirements.txt
COPY ./main.py /main.py

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

CMD redis-server --daemonize yes \
    && gunicorn --bind 0.0.0.0:$PORT -w 5 -k uvicorn.workers.UvicornWorker main:app
