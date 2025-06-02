# Running Python program in docker

(TO BE UPDATED...)

**To run one or several script inside a docker:**

Define a Dockerfile for each script such as

```
# syntax=docker/dockerfile:1
FROM python:3.8.13
RUN apt-get update
WORKDIR /dataflux
COPY ../dataflux/ .
RUN pip install -r ./requirements.txt
CMD [ "python", "./dataflux.py --flow ./flow/flow_ttn_template.json" ]
```

Declare the new docker in the *docker-compose.yml* file

```
version: '3.7'
services:
  flow_ttn_template:
    build:
      context: .
      dockerfile: ./Dockerfile_flow_ttn_template
    restart: always
```

## First build of "flow_orange_loraship-fifo" docker on the VPS

Put your project folder on the VPS with
```
git clone https://gitlab.ifremer.fr/sb2-team/dataflux-agent.git
```

Move into the folder "flow_orange_loraship-fifo":
```
cd dataflux-agent/docker/flow_orange_loraship-fifo/
```

Build and start the docker with

```
sudo docker compose up -d
```

## Updating an existing docker on the VPS

Move into the folder where the docker-compose.yml file is.<br/>
For example, for the docker "flow_orange_loraship-fifo", move into the following folder:
```
cd dataflux-agent/docker/flow_orange_loraship-fifo/
```

Stop the docker container:
```
sudo docker compose stop
```

Pull your last modifications from GitHub or GitLab:
```
git pull
```

Rebuild your docker container:
```
sudo docker compose build
```

Restart your docker container:
```
sudo docker compose up -d
```

## Useful commands

To check which dockers are on the server, use

```
docker ps -a
```

To check the last 50 logs of a docker, use
```
docker logs -n 50 <container_id>
```

To save a docker container logs in a file, use
```
sudo docker logs <container_id> filename.log 2>&1
```