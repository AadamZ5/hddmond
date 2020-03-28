FROM nginx:stable-alpine

RUN apk update
RUN apk add sshfs