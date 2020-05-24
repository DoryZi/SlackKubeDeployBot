FROM python:3.6-slim

ENV PYTHONUNBUFFERED 1
ENV LANGUAGE "en_US:en"
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y gcc libc-dev locales git-core
RUN touch /usr/share/locale/locale.alias
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && locale-gen

WORKDIR /slackbot
COPY ./requirements.txt /slackbot
RUN pip install -r requirements.txt

COPY . /slackbot


CMD ["python", "./slackbot.py"]
