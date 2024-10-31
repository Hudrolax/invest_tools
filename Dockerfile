FROM python:3.12.2-alpine3.18

ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /tmp/requirements.txt
COPY ./requirements.dev.txt /tmp/requirements.dev.txt
COPY ./scripts /scripts
COPY ./app /app

WORKDIR /app

ENV PYTHONPATH=/app

EXPOSE 9000

ARG DEV=false
RUN python -m venv /py && \
  /py/bin/pip install --upgrade pip && \
  apk add --update --no-cache --virtual .build-deps \
    gcc \
    linux-headers \
    python3-dev \
    libffi-dev \
    musl-dev \ 
    postgresql-dev && \
  apk add --no-cache postgresql-libs \
    postgresql-client && \
  /py/bin/pip install --upgrade pip && \
  /py/bin/pip install --no-cache-dir -r /tmp/requirements.txt && \
  if [ $DEV = "true" ]; \
  then /py/bin/pip install -r /tmp/requirements.dev.txt ; \
  fi && \
  apk del .build-deps && \
  rm -rf /tmp && \
  chmod -R +x /scripts && \
    adduser \
  --disabled-password \
  --no-create-home \
  www

ENV PATH="/scripts:/py/bin:$PATH"

USER www

CMD ["run.sh"]
