FROM python:alpine

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

ENV FLASK_APP=wargame
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wargame:app"]
