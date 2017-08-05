FROM python:3.6-alpine

LABEL maintainer "s@muelcolvin.com"

RUN apk --update --no-cache add postgresql-dev gcc g++ musl-dev libuv make \
 && rm -rf /var/cache/apk/*

ADD ./requirements.txt /home/root/requirements.txt
RUN pip install --no-cache-dir -r /home/root/requirements.txt \
 && rm /home/root/requirements.txt

ADD ./app /home/root/app
ADD ./run.py /home/root/run.py

WORKDIR /home/root
ENTRYPOINT ["./run.py"]
CMD ["web"]
