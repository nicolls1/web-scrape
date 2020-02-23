FROM python:3
COPY requirements.txt .
RUN pip install -r requirements.txt

RUN wget -O /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.1/dumb-init_1.2.1_amd64
RUN chmod +x /usr/local/bin/dumb-init

COPY . /api
WORKDIR /api

ENTRYPOINT ["/usr/local/bin/dumb-init", "--"]

CMD python app.py
