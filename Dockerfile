FROM python:alpine

WORKDIR /app

COPY requirements/* requirements/
RUN pip install -r requirements/prod.txt

COPY . .

ENV FLASK_APP=wargame
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wargame:app"]
