# The world in which every episode runs. Nothing but Python and pytest.
FROM python:3.12-slim
RUN pip install --no-cache-dir pytest==8.3.5 && rm -rf /root/.cache
WORKDIR /work
CMD ["sleep", "infinity"]
