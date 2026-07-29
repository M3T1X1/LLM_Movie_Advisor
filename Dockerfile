FROM ubuntu:latest
LABEL authors="debian"

ENTRYPOINT ["top", "-b"]