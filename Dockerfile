# ---- Stage 1: build the C++ nodes ------------------------------------------
FROM ubuntu:24.04 AS build
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential cmake git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY cpp/ cpp/
RUN cmake -S cpp -B build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build --target sim_node tracker_node -j"$(nproc)"

# ---- Stage 2: small runtime image ------------------------------------------
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir boto3
ENV PATH="/opt/venv/bin:${PATH}"

COPY --from=build /src/build/sim_node /src/build/tracker_node /usr/local/bin/
COPY worker/worker.py /app/worker.py

RUN useradd --system --no-create-home app
USER app

# Configuration comes from environment variables: QUEUE_URL, TABLE_NAME,
# AWS_REGION, CAPSULE_ID. Credentials come from the ECS task role.
CMD ["python3", "/app/worker.py"]
