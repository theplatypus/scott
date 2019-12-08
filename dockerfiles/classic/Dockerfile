FROM continuumio/anaconda

# RUN apt-get update --fix-missing && apt-get install -y wget bzip2 ca-certificates \
# 	libglib2.0-0 libxext6 libsm6 libxrender1

# RUN wget --quiet https://repo.anaconda.com/archive/Anaconda2-5.3.0-Linux-x86_64.sh -O ~/anaconda.sh && \
# 	/bin/bash ~/anaconda.sh -b -p /opt/conda && \
# 	rm ~/anaconda.sh && \
# 	ln -s /opt/conda/etc/profile.d/conda.sh /etc/profile.d/conda.sh && \
# 	echo ". /opt/conda/etc/profile.d/conda.sh" >> ~/.bashrc

# CONDA ENV

RUN yes | /opt/conda/bin/conda create -c rdkit -n scott python=3.6 jupyter anaconda rdkit gensim

RUN echo "conda activate scott" >> ~/.bashrc
ENV PATH /opt/conda/envs/scott/bin:$PATH

# DEB PACKAGES 

RUN apt-get update && apt-get install -y python3-lxml


# SCOTT Package 
# —————————————————————————————————

RUN mkdir /opt/scott && \
	mkdir /opt/notebooks && \
	mkdir /home/scott

WORKDIR /opt/scott 

COPY . .

RUN python setup.py install

# WORKDIR /home/scott

CMD ["/bin/bash"]
