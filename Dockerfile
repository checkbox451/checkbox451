FROM ubuntu:20.04

ARG ACSK
ARG LOGIN
ARG KEY
ARG PASSWORD
ARG API_URL

ARG KEY_PATH=/key.dat
ARG PASSWORD_FILE=/password.txt

ARG DOWNLOAD_URL=https://agents.checkbox.in.ua/agents/checkboxAgentSign/Linux/checkbox.sign-linux-x86_64.zip
ARG WORKDIR=/checkbox.sign

ENV ACSK=$ACSK
ENV LOGIN=$LOGIN
ENV API_URL=$API_URL
ENV PASSWORD_FILE=$PASSWORD_FILE
ENV KEY_PATH=$KEY_PATH

RUN apt-get update
RUN apt-get install -y locales unzip wget

RUN wget $DOWNLOAD_URL
RUN unzip *.zip -d $WORKDIR
RUN rm -f *.zip

COPY $KEY $KEY_PATH
RUN test $PASSWORD && echo -n $PASSWORD > $PASSWORD_FILE || :

RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8

WORKDIR $WORKDIR
CMD echo $ACSK | ./srso_signer setup && ./srso_signer start --login $LOGIN --password-file $PASSWORD_FILE ${API_URL:+--api-url $API_URL }--infinity $KEY_PATH
