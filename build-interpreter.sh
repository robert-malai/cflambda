#!/usr/bin/env bash
docker build --no-cache --tag ${PWD##*/}-interpreter:latest \
    --build-arg AWS_DEFAULT_REGION=$(aws configure get region) \
    --build-arg AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id) \
    --build-arg AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key) \
    - << EOF
FROM python:3.7

ARG AWS_DEFAULT_REGION
ENV AWS_DEFAULT_REGION=\$AWS_DEFAULT_REGION

ARG AWS_ACCESS_KEY_ID
ENV AWS_ACCESS_KEY_ID=\$AWS_ACCESS_KEY_ID

ARG AWS_SECRET_ACCESS_KEY
ENV AWS_SECRET_ACCESS_KEY=\$AWS_SECRET_ACCESS_KEY

RUN pip install --upgrade boto3 awscli
RUN git config --global credential.helper '!aws codecommit credential-helper \$@'
RUN git config --global credential.UseHttpPath true

$(cat app/requirements.txt |  awk '{print "RUN pip install --no-cache-dir " $1}')

EOF