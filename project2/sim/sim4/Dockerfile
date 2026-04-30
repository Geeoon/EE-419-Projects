FROM alpine:latest
WORKDIR /ee419

RUN apk add python3

COPY ./content_server.py .
COPY ./sim/sim4/example4.conf .

CMD ["python3", "content_server.py", "-c", "example4.conf"]
