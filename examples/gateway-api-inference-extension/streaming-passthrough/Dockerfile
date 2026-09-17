FROM python:3.11-slim

WORKDIR /app

# Copy and install RAGEngine dependencies (for OutputGuardrails)
COPY presets/ragengine/requirements.txt /tmp/ragengine-requirements.txt
RUN pip install --no-cache-dir -r /tmp/ragengine-requirements.txt

# Copy and install ext_proc dependencies
COPY examples/gateway-api-inference-extension/streaming-passthrough/requirements.txt /tmp/extproc-requirements.txt
RUN pip install --no-cache-dir -r /tmp/extproc-requirements.txt

# Copy presets (guardrails library, for future use)
COPY presets/ ./presets/

# Copy ext_proc server
COPY examples/gateway-api-inference-extension/streaming-passthrough/ext_proc_server.py .

# Set Python path
ENV PYTHONPATH=/app/presets

# Run as non-root
USER 1000:1000

ENTRYPOINT ["python", "ext_proc_server.py"]
