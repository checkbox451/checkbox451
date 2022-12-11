FROM ubuntu:20.04

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update
RUN apt-get install -y --no-install-recommends bash locales python3 python3-pip sudo tzdata

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV TZ Europe/Kiev

WORKDIR /checkbox451_bot
COPY . .
RUN mv drop-privileges.sh /
RUN pip3 install .
RUN rm -rf *

ENTRYPOINT ["/drop-privileges.sh", "config.yaml"]
CMD ["python3", "-m", "checkbox451_bot"]
