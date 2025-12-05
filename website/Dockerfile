FROM python:3.13.2-bullseye

RUN apt-get update && \
    apt-get install -y locales  && \
    sed -i '/fr_CH.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen

ENV LANG=fr_CH.UTF-8
ENV LANGUAGE=fr_CH:fr
ENV LC_ALL=fr_CH.UTF-8

RUN mkdir /app
RUN mkdir /app/data

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app
WORKDIR /app
