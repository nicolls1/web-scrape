# Web Scrape

## Local setup

In a python environment:
```
pip install -r requirements.txt
python app.py
```

## Docker Setup

With docker and docker compose installed:
```
docker build . --tag scrape-api:latest
docker-compose up
```

## Using App

App is running on port 8888 and accepts a GET action at the root. 
The endpoint takes a single `url` query parameter as so:
`
http://localhost:8888/?url=https://www.w3schools.com/tags/att_a_href.asp
`