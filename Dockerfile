FROM rayproject/ray-ml:2.9.2-py310

USER root

# Essential tools to support core dumps
RUN apt-get update && apt-get install -y gdb && \
    rm -rf /var/lib/apt/lists/*

# Allow unlimited core dump
RUN echo '* soft core unlimited\n* hard core unlimited' >> /etc/security/limits.conf
RUN ulimit -c unlimited

# Create a dedicated directory for core dumps
RUN mkdir -p /var/coredumps && chmod 1777 /var/coredumps

WORKDIR /serve_app
COPY requirements.txt .
RUN pip install -r requirements.txt

ENV TZ=Asia/Singapore