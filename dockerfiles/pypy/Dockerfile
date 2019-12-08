FROM pypy


#DEB PACKAGES

RUN apt-get update && apt-get install -y python3-lxml
#RUN pypy3 -m easy_install ipython
#RUN alias pypython="/usr/local/share/pypy/ipython"

RUN pip install virtualenv
#RUN mkdir /opt/venv


ENV VIRTUAL_ENV=/opt/venv
RUN virtualenv --python=pypy3 $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

#RUN virtualenv -p pypy3 /opt/venv
#RUN source /opt/venv/bin/activate
RUN pip install ipython joblib jupyter redis
#RUN alias pypy="/opt/venv/pypy3"


# SCOTT Package
# —————————————————————————————————

RUN mkdir /opt/scott && \
        mkdir /opt/notebooks && \
        mkdir /home/scott

WORKDIR /opt/scott

COPY . .

#RUN python setup.py install

WORKDIR /opt/scott

# Add Tini. Tini operates as a process subreaper for jupyter. This prevents
# kernel crashes.
#ENV TINI_VERSION v0.18.0
#ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
#RUN chmod +x /tini
#ENTRYPOINT ["/tini", "--"]

EXPOSE 8888
#CMD ["jupyter", "notebook", "--port=8888", "--no-browser", "--ip=0.0.0.0", "--allow-root"]
CMD ["bash"]
