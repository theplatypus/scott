FROM python:latest

# Rust toolchain (needed to build the PyO3 extension)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# System deps for rdkit
RUN apt-get update && apt-get install -y --no-install-recommends \
	libxml2 \
	&& rm -rf /var/lib/apt/lists/*

# Python build tools
RUN pip install --no-cache-dir maturin uv

# Scott package
WORKDIR /opt/scott
COPY . .

# Build the Rust extension and install with all extras
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

RUN uv pip install -e '.[rdkit,dev]'
RUN uv pip install jupyter
RUN maturin develop --release

# Workspace
RUN mkdir -p /opt/notebooks /home/scott

EXPOSE 8888
CMD ["jupyter", "notebook", "--notebook-dir=/opt/notebooks", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
