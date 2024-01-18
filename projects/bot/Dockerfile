FROM amd64/python:3.12.1-slim as base

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
COPY ./googleauth/ /shared/googleauth/

RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main --no-dev

FROM amd64/python:3.12.1-slim

RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

COPY --from=base /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

WORKDIR /bot
COPY src/ ./src/  
RUN chmod +x src/start.py
CMD ["python", "src/start.py"]