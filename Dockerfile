FROM python:3.11-slim

COPY db lib service.py settings.toml requirements.txt .

RUN pip install -r requirements.txt

CMD ["python","service.py"]
