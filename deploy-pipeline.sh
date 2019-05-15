#!/usr/bin/env bash
aws cloudformation deploy \
    --template pipeline.yml \
    --stack-name ${PWD##*/}-pipeline \
    --capabilities CAPABILITY_IAM \
    --capabilities CAPABILITY_NAMED_IAM