# FROM muccg/rdrf-builder
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
  nodejs-legacy \
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
RUN pip install -r dev-requirements.txt
# TODO this should be installed only in the test images?
RUN pip install -r test-requirements.txt

VOLUME ["/data"]

FROM python:3.6-slim

ENV PYTHONPATH="/app/rdrf/:${PYTHONPATH}"
ENV DJANGO_SETTINGS_MODULE rdrf.settings

# RUN apt-get update && apt-get install -y --no-install-recommends \
#    libxml2 \
#   && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN apt-get update && apt-get install -y --no-install-recommends \
  # Base
  # TODO check if requirements are needed
  gettext \
  libpcre3 \
  libpq5 \
  mime-support \
  nodejs-legacy \
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

EXPOSE 8000

WORKDIR /app

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["runserver_plus"]
