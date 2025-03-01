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
    openjdk-11-jre-headless \
    parallel \
    pigz \
    python3 \
    python3-pip \
    python-is-python3 \
    python3-venv \
    wget \
    unzip \
    zlib1g-dev \
    hmmer \
    cd-hit \
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

# Install TransDecoder
WORKDIR ${TOOLS}
RUN wget https://github.com/TransDecoder/TransDecoder/archive/refs/tags/TransDecoder-v5.7.1.tar.gz \
    && tar -zxvf TransDecoder-v5.7.1.tar.gz \
    && rm TransDecoder-v5.7.1.tar.gz \
    && ln -s ${TOOLS}/TransDecoder-TransDecoder-v5.7.1/TransDecoder* ${TOOLS}/bin/

# Install BLAST
WORKDIR ${TOOLS}
RUN wget ftp://ftp.ncbi.nlm.nih.gov/blast/executables/blast+/2.9.0/ncbi-blast-2.9.0+-x64-linux.tar.gz \
    && tar -zxvf ncbi-blast-2.9.0+-x64-linux.tar.gz \
    && rm ncbi-blast-2.9.0+-x64-linux.tar.gz \
    && ln -s ${TOOLS}/ncbi-blast-2.9.0+/bin/* ${TOOLS}/bin/

# Install mmseqs2
WORKDIR ${TOOLS}
RUN wget https://mmseqs.com/latest/mmseqs-linux-avx2.tar.gz \
    && tar xvfz mmseqs-linux-avx2.tar.gz \
    && ln -s ${TOOLS}/mmseqs/bin/* ${TOOLS}/bin/ \
    && rm mmseqs-linux-avx2.tar.gz

# Install eggNOG-mapper
WORKDIR ${TOOLS}
RUN git clone https://github.com/eggnogdb/eggnog-mapper.git \
    && cd eggnog-mapper \
    && python3 -m pip install -r requirements.txt \
    && python3 setup.py install

# Create working directory
RUN mkdir -p /data
WORKDIR /data

# Add annotation script
COPY annotate_assembly.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/annotate_assembly.sh

# Set default command
ENTRYPOINT ["/usr/local/bin/annotate_assembly.sh"]