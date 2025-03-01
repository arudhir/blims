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

# Install SRA Toolkit
WORKDIR ${TOOLS}
RUN wget https://ftp-trace.ncbi.nlm.nih.gov/sra/sdk/3.1.1/sratoolkit.3.1.1-ubuntu64.tar.gz \
    && tar -zxvf sratoolkit.3.1.1-ubuntu64.tar.gz \
    && ln -s ${TOOLS}/sratoolkit.3.1.1-ubuntu64/bin/* ${TOOLS}/bin/ \
    && rm sratoolkit.3.1.1-ubuntu64.tar.gz

# Install fastp
WORKDIR ${TOOLS}/bin
RUN wget http://opengene.org/fastp/fastp \
    && chmod a+x ./fastp

# Install BBMap suite
WORKDIR ${TOOLS}
RUN wget https://sourceforge.net/projects/bbmap/files/BBMap_39.01.tar.gz \
    && tar -xzf BBMap_39.01.tar.gz \
    && rm BBMap_39.01.tar.gz \
    && ln -s ${TOOLS}/bbmap/*.sh ${TOOLS}/bin/

# Create working directory
RUN mkdir -p /data
WORKDIR /data

# Add pipeline script
COPY process_reads.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/process_reads.sh

# Set default command
ENTRYPOINT ["/usr/local/bin/process_reads.sh"]