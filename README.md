helpmanual.io.search
====================

Your new aiohttp app!

To install:

```
apt update
apt upgrade
apt show nginx
apt install nginx git
nginx -V
apt install python-pip build-essential
sudo apt install postgresql-9.5 postgresql-contrib-9.5 postgresql-server-dev-9.5 python3.5-dev
pip install -U pip virtualenv

ssh-keygen -t rsa -b 4096 -C "production@scolvin.com"
cat ~/.ssh/id_rsa.pub
git clone git@github.com:samuelcolvin/helpmanual.io.search.git
cd helpmanual.io.search
virtualenv -p /usr/bin/python3.5 env
search env/bin/activate
pip install -r requirements.txt


cp conf/gunicorn.service /etc/systemd/system/
systemctl enable gunicorn

cp conf/nginx.conf /etc/nginx/sites-enabled/default
nginx -t
service nginx start
```
