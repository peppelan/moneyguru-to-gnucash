FROM ubuntu:14.04

RUN apt-get update && apt-get -y install vim gnucash python-gnucash
