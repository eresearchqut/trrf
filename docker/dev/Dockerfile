# FROM muccg/rdrf-builder
FROM python:3.8.0 as builder

ENV PYTHONUNBUFFERED 1
#
RUN apt-get update && apt-get install -y --no-install-recommends \
#  gettext \
#  libpcre3 \
#  libpq5 \
#  mime-support \
#  nodejs \
#  unixodbc \
  build-essential \
#  git \
#  gzip \
#  libpcre3-dev \
#  libpq-dev \
#  libssl-dev \
#  libyaml-dev \
  unixodbc-dev \
#  zlib1g-dev \
  && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN mkdir -p /requirements
WORKDIR /requirements

COPY requirements/requirements.txt ./
RUN pip install -r requirements.txt

COPY requirements/dev-requirements.txt ./
RUN pip install -r dev-requirements.txt

COPY requirements/test-requirements.txt ./
RUN pip install -r test-requirements.txt

VOLUME ["/data"]

FROM python:3.8.0-slim

ENV PYTHONPATH="/app/rdrf/:${PYTHONPATH}"
ENV DJANGO_SETTINGS_MODULE rdrf.settings
ENV STATIC_ROOT="/data/static"
ENV WRITABLE_DIRECTORY="/data/scratch"
ENV LOCALE_PATHS="/data/translations/locale"
ENV LOG_DIRECTORY="/data/log"
ENV MEDIA_ROOT="/data/static/media"

RUN apt-get update && apt-get install -y --no-install-recommends \
  # Base
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
COPY --from=builder /requirements/ .

RUN pip install -r requirements.txt
RUN pip install -r dev-requirements.txt
RUN pip install -r test-requirements.txt

RUN rm -Rf /root/.cache

COPY docker/dev/docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

VOLUME ["/app", "/data"]

ENV HOME /data
WORKDIR /data

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["runserver_plus"]
