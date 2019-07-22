# Container to build our prod image
# TODO upgrade to 3.7 (both here and main image below)
FROM python:3.6 as builder

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y --no-install-recommends \
  # TODO check if requirements are needed
  # Base
  gettext \
  libpcre3 \
  libpq5 \
  mime-support \
  nodejs \
  unixodbc \
  # Builder
  build-essential \
  git \
  gzip \
  libpcre3-dev \
  libpq-dev \
  libssl-dev \
  libyaml-dev \
  unixodbc-dev \
  zlib1g-dev \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mkdir -p /requirements
WORKDIR /requirements

# RUN env | sort

# Add our python deps in multiple docker layers
# hgvs was failing due to lack of nose, hence the order

COPY requirements/* ./

RUN pip install -r requirements.txt


# Container used to build rdrf frontend
FROM node:9.11.1 as nodebuilder

# TODO separate dev/prod entrypoints?
COPY docker/dev/docker-entrypoint-node.sh /docker-entrypoint-node.sh
COPY . /app

WORKDIR /app/rdrf/rdrf/frontend

RUN /docker-entrypoint-node.sh build

# Actual image we are building
FROM python:3.6-slim

ENV PYTHONUNBUFFERED 1

ENV PYTHONPATH="/app/rdrf/"
ENV DJANGO_SETTINGS_MODULE rdrf.settings

ENV PROJECT_NAME trrf
ENV PROJECT_SOURCE https://github.com/eresearchqut/trrf.git
ENV DEPLOYMENT prod
ENV PRODUCTION 1
ENV DEBUG 0
ENV STATIC_ROOT /data/static
ENV WRITABLE_DIRECTORY /data/scratch
ENV MEDIA_ROOT /data/static/media
ENV LOG_DIRECTORY /data/log
ENV LOCALE_PATHS /data/translations/locale
ENV DJANGO_SETTINGS_MODULE rdrf.settings

RUN mkdir /app

RUN addgroup --gid 1000 django \
  && adduser --disabled-password --home /data --no-create-home --system -q --uid 1000 --ingroup django django \
  && mkdir /data \
  && chown django:django /data \
  && chown django:django /app

RUN apt-get update && apt-get install -y --no-install-recommends \
  # Base
  # TODO check if requirements are needed
  gettext \
  libpcre3 \
  libpq5 \
  mime-support \
  nodejs \
  unixodbc \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mkdir /requirements
WORKDIR /requirements

COPY --from=builder /root/.cache /root/.cache
COPY --from=builder /requirements/requirements.txt .

RUN pip install -r requirements.txt

RUN rm -Rf /root/.cache

# Currently just using the dev entrypoint for prod as well
# TODO separate or move one level up
COPY docker/dev/docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

VOLUME ["/data"]
ENV HOME /data

EXPOSE 9000

COPY --chown=django:django . /app
# RUN chown -R django /app

# COPY --from=nodebuilder /app/root/.cache /root/.cache

USER django
WORKDIR /data

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uwsgi"]

