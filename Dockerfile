FROM python:3.12

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

RUN apt-get -y update
RUN apt-get -y upgrade
RUN apt-get install -y ffmpeg

COPY ./ /app

CMD gunicorn app:app & python3 bot.py
