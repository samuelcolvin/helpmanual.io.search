FROM python:3.7-slim

LABEL maintainer "s@muelcolvin.com"

# https://github.com/pypa/pip/issues/6197
RUN pip install pip==18.1

ADD ./requirements.txt /home/root/requirements.txt
RUN pip install -r /home/root/requirements.txt

ADD ./app /home/root/app
ADD ./run.py /home/root/run.py

WORKDIR /home/root
ENTRYPOINT ["./run.py"]
CMD ["web"]
