FROM python:3.12.1-slim-bookworm as base
ARG ENV
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gcc \
    git

ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN curl -sSL https://install.python-poetry.org | python3 -

COPY ./poetry.lock ./pyproject.toml ./
COPY ./db/ /shared/db/

RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main --no-dev

FROM python:3.12.1-slim-bookworm

RUN addgroup --system app && adduser --system --group app

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y nginx && \
    apt-get install -y curl && \
    apt-get install -y sudo && \
    rm -rf /var/lib/apt/lists/*

COPY --from=base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

WORKDIR /api
RUN touch creds.json
COPY nginx.conf /etc/nginx/nginx.conf
COPY src/ src/  
COPY instance/ instance/
COPY entrypoint.sh ./
RUN chmod +x ./entrypoint.sh
RUN chown -R app:app /api
WORKDIR /api/src
EXPOSE 80
ENTRYPOINT [ "../entrypoint.sh", "production" ]