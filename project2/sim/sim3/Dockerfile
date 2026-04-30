FROM alpine:latest
WORKDIR /ee419

RUN apk add python3

COPY ./content_server.py .
COPY ./sim/sim3/example3.conf .

CMD ["python3", "content_server.py", "-c", "example3.conf"]
