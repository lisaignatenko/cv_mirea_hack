FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# ---- System packages for OpenCV / cv2 ----
# libgl1      -> provides libGL.so.1
# libglib2.0-0 -> avoids common GLib-related runtime errors with OpenCV
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 999 nonroot \
 && useradd --system --gid 999 --uid 999 --create-home nonroot

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Install project dependencies (no project code yet, for better caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Now copy the actual project code and install it into the venv
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["uvicorn"]

USER nonroot

CMD ["cv.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
