FROM pypy:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
	libxml2 \
	&& rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir ipython jupyter pytest ruff

# Scott package (legacy backend — PyPy cannot build PyO3 extensions)
# Skip maturin build backend: just put the source on PYTHONPATH
WORKDIR /opt/scott
COPY . .

ENV PYTHONPATH=/opt/scott
ENV SCOTT_BACKEND=legacy

RUN mkdir -p /opt/notebooks /home/scott

EXPOSE 8888
CMD ["jupyter", "notebook", "--notebook-dir=/opt/notebooks", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
