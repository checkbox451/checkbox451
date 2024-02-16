FROM python:3.12-slim

ENV DEBIAN_FRONTEND noninteractive
ENV PIP_NO_CACHE_DIR 1
ENV PIP_ROOT_USER_ACTION ignore
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV TZ Europe/Kiev

RUN apt-get update
RUN apt-get install -y --no-install-recommends sudo

WORKDIR /checkbox451_bot
COPY . .
RUN mv drop-privileges.sh /
RUN pip3 install .
RUN rm -rf *

ENTRYPOINT ["/drop-privileges.sh", "config.yaml"]
CMD ["python3", "-m", "checkbox451_bot"]
