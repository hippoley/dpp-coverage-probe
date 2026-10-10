# Reproducible container image for the real OpenDPP + IDTA validation API.
FROM node:22-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ARG OPENDPP_COMMIT=20211ecc2b63eb7664c571a8d629aeeed364491e
RUN git clone https://github.com/OpenDPP/opendpp-interop.git /opt/opendpp \
    && git -C /opt/opendpp checkout --detach "${OPENDPP_COMMIT}" \
    && test "$(git -C /opt/opendpp rev-parse HEAD)" = "${OPENDPP_COMMIT}" \
    && cd /opt/opendpp/validate && npm ci --omit=dev

RUN python3 -m venv /opt/dpp-venv \
    && /opt/dpp-venv/bin/pip install --no-cache-dir aas_test_engines==1.0.3

WORKDIR /app
COPY validate_dpp.py api_server.py dpp_client.py batch_validate.py /app/
ENV PATH="/opt/dpp-venv/bin:${PATH}" OPENDPP_CHECKOUT=/opt/opendpp
USER node
EXPOSE 8765
CMD ["python3", "api_server.py", "--host", "0.0.0.0", "--port", "8765", "--opendpp", "/opt/opendpp"]
