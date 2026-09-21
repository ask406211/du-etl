# ---- build stage: resolve dependencies into a self-contained venv ----
FROM python:3.13-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN pip install .

# ---- runtime stage: just the venv, no build tooling ----
FROM python:3.13-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Run as a non-root user: a container breakout is far less useful without root.
RUN useradd --create-home --uid 10001 appuser
COPY --from=builder /opt/venv /opt/venv

USER appuser
WORKDIR /home/appuser

# A batch job, not a server: it runs to completion and exits.
ENTRYPOINT ["ducks-unlimited"]
