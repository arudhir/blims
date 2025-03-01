FROM --platform=linux/amd64 ubuntu:20.04

# Set environment variables
ENV TOOLS=/tools
ENV DEBIAN_FRONTEND=noninteractive
ENV PATH=$PATH:$TOOLS/bin:/usr/local/bin

# Install common system dependencies
RUN apt-get update && apt-get install -y \
    autotools-dev \
    automake \
    cmake \
    curl \
    git \
    libbz2-dev \
    libdatetime-perl \
    libdigest-md5-perl \
    liblzma-dev \
    libncurses5-dev \
    libncursesw5-dev \
    libxml-simple-perl \
    parallel \
    pigz \
    python3 \
    python3-pip \
    python-is-python3 \
    python3-venv \
    pipx \
    wget \
    unzip \
    zlib1g-dev \
    awscli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create tools directory
RUN mkdir -p ${TOOLS}/bin

# Install seqtk (common utility for all jobs)
WORKDIR ${TOOLS}
RUN git clone https://github.com/lh3/seqtk.git \
    && cd seqtk \
    && make \
    && cp seqtk ${TOOLS}/bin/

# Install seqkit (common utility for all jobs)
WORKDIR ${TOOLS}
RUN wget https://github.com/shenwei356/seqkit/releases/download/v2.9.0/seqkit_linux_amd64.tar.gz \
    && tar xvf seqkit_linux_amd64.tar.gz \
    && cp seqkit ${TOOLS}/bin/ \
    && rm seqkit_linux_amd64.tar.gz

# Install Python dependencies for database update
RUN pip3 install duckdb pandas numpy scipy scikit-learn matplotlib plotly boto3

# Create working directory
RUN mkdir -p /data
WORKDIR /data

# Add database update script
COPY update_database.sh /usr/local/bin/
COPY update_database.py /usr/local/bin/
RUN chmod +x /usr/local/bin/update_database.sh

# Set default command
ENTRYPOINT ["/usr/local/bin/update_database.sh"]