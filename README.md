helpmanual.io.search
====================

To create machine

```
export SCALEWAY_ORGANIZATION='...'
export SCALEWAY_TOKEN='...'
export MACHINE_DOCKER_INSTALL_URL='https://web.archive.org/web/20170623081500/https://get.docker.com'
docker-machine create -d scaleway --scaleway-commercial-type VC1S --scaleway-name helpmanual helpmanual
```
