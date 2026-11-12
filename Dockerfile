FROM python:3.12-slim

# The entrypoint uses only the standard library, so nothing is installed.
COPY entrypoint.py /entrypoint.py

ENTRYPOINT ["python", "/entrypoint.py"]
