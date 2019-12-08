FROM openjdk:8

# SPARK 
# —————————————————————————————————

# Scala related variables.
ARG SCALA_VERSION=2.12.2
ARG SCALA_BINARY_ARCHIVE_NAME=scala-${SCALA_VERSION}
ARG SCALA_BINARY_DOWNLOAD_URL=http://downloads.lightbend.com/scala/${SCALA_VERSION}/${SCALA_BINARY_ARCHIVE_NAME}.tgz

# SBT related variables.
ARG SBT_VERSION=0.13.15
ARG SBT_BINARY_ARCHIVE_NAME=sbt-$SBT_VERSION
ARG SBT_BINARY_DOWNLOAD_URL=https://dl.bintray.com/sbt/native-packages/sbt/${SBT_VERSION}/${SBT_BINARY_ARCHIVE_NAME}.tgz

# Spark related variables.
ARG SPARK_VERSION=2.2.0
ARG SPARK_BINARY_ARCHIVE_NAME=spark-${SPARK_VERSION}-bin-hadoop2.7
ARG SPARK_BINARY_DOWNLOAD_URL=http://d3kbcqa49mib13.cloudfront.net/${SPARK_BINARY_ARCHIVE_NAME}.tgz

# Configure env variables for Scala, SBT and Spark.
# Also configure PATH env variable to include binary folders of Java, Scala, SBT and Spark.
ENV SCALA_HOME  /usr/local/scala
ENV SBT_HOME    /usr/local/sbt
ENV SPARK_HOME  /usr/local/spark
ENV PATH        $JAVA_HOME/bin:$SCALA_HOME/bin:$SBT_HOME/bin:$SPARK_HOME/bin:$SPARK_HOME/sbin:$PATH

# Download, uncompress and move all the required packages and libraries to their corresponding directories in /usr/local/ folder.
RUN apt-get -yqq update && \
    apt-get install -yqq vim screen tmux && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /tmp/* && \
    wget -qO - ${SCALA_BINARY_DOWNLOAD_URL} | tar -xz -C /usr/local/ && \
    wget -qO - ${SBT_BINARY_DOWNLOAD_URL} | tar -xz -C /usr/local/  && \
    wget -qO - ${SPARK_BINARY_DOWNLOAD_URL} | tar -xz -C /usr/local/ && \
    cd /usr/local/ && \
    ln -s ${SCALA_BINARY_ARCHIVE_NAME} scala && \
    ln -s ${SPARK_BINARY_ARCHIVE_NAME} spark && \
    cp spark/conf/log4j.properties.template spark/conf/log4j.properties && \
    sed -i -e s/WARN/ERROR/g spark/conf/log4j.properties && \
    sed -i -e s/INFO/ERROR/g spark/conf/log4j.properties


# Use Python3 in PySpark 
# —————————————————————————————————

# install python3
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    python3-lxml python-rdkit librdkit1 rdkit-data

RUN pip3 install jupyter && mkdir /root/notebook

RUN apt-get install -y 

# use python3 as default for spark-submit script
RUN echo "PYSPARK_PYTHON=python3" >> /usr/local/spark/conf/spark-env.sh


# Openbabel Package 
# —————————————————————————————————

RUN mkdir /opt/openbabel 

WORKDIR /opt/openbabel

RUN apt-get install -y openbabel libopenbabel-dev \
    python python-setuptools python-dev python-augeas \
     gcc swig dialog

RUN cp -R /usr/include/openbabel-2.0 /usr/local/include/openbabel-2.0

RUN wget https://files.pythonhosted.org/packages/9c/30/eb9c3d3d3b86981f6c6a7b8eceb6f4a13b9a12673efbc842b7cebe0ce39a/openbabel-2.4.1.tar.gz && \
    tar -xvf openbabel-2.4.1.tar.gz 

WORKDIR /opt/openbabel/openbabel-2.4.1

RUN python3 setup.py install

# SCOTT Package 
# —————————————————————————————————

RUN mkdir /opt/scott && \
	mkdir /opt/notebooks && \
	mkdir /home/scott

WORKDIR /opt/scott

COPY . .

RUN python3 setup.py install

WORKDIR /home/scott

# Expose ports for monitoring.
# SparkContext web UI on 4040 -- only available for the duration of the application.
# Spark master’s web UI on 8080.
# Spark worker web UI on 8081.
EXPOSE 4040 8080 8081

CMD ["/bin/bash"]
