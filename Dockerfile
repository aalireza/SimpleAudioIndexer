FROM ubuntu

RUN apt-get update && apt-get install -y software-properties-common
RUN add-apt-repository universe
RUN apt-get update && apt-get install -y python3 python3-pip python-pip sox

RUN pip install SimpleAudioIndexer
RUN pip3 install SimpleAudioIndexer

CMD tail -F -n0 /etc/hosts
