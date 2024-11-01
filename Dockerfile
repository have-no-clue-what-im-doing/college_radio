FROM ubuntu:latest

ENV DEBIAN_FRONTEND=noninteractive


RUN apt-get update -y && \
    apt-get install -y python3 python3-pip python3-venv software-properties-common libpq-dev && \
    apt-add-repository ppa:marin-m/songrec -y && \
    apt-get update -y && \
    apt-get install -y songrec && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app


COPY . /app


RUN python3 -m venv venv && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt


CMD ["/app/venv/bin/python", "college_radio.py"]

