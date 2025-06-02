# syntax=docker/dockerfile:1
FROM python:3.7.3
WORKDIR /dataflux
COPY ./ .
RUN pip install -r ./requirements.txt
CMD [ "python", "-u", "./dataflux.py", "--flow", "./flow/flow_ttn_template.json" ]