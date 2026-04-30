FROM alpine:latest
WORKDIR /ee419

RUN apk add python3

COPY ./content_server.py .
COPY ./sim/sim2/example2.conf .

CMD ["python3", "content_server.py", "-c", "example2.conf"]
