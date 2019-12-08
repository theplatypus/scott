FROM debian:latest

# PYTHON

# install python3
RUN apt-get update && apt-get install -y python3 python3-pip python3-lxml

RUN pip3 install jupyter && mkdir /root/notebook
RUN pip3 install cython

RUN apt-get install -y python-rdkit librdkit1 rdkit-data

# install scott

RUN mkdir /opt/scott
WORKDIR /opt/scott 

COPY . .

RUN python3 setup.py install

CMD ["/bin/bash"]
