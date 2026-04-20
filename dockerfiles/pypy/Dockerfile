FROM pypy:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
	libxml2 \
	&& rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir ipython pytest ruff

# Scott package (legacy backend — PyPy cannot build PyO3 extensions)
# Skip maturin build backend: just put the source on PYTHONPATH
WORKDIR /opt/scott
COPY . .

ENV PYTHONPATH=/opt/scott
ENV SCOTT_BACKEND=legacy

RUN mkdir -p /opt/notebooks /home/scott

CMD ["bash"]
