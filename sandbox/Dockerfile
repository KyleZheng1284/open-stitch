FROM node:20-slim

# Install system dependencies: FFmpeg + Chromium (needed by @remotion/renderer)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        chromium \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Tell Puppeteer/Remotion to use the installed Chromium
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV REMOTION_CHROME_EXECUTABLE=/usr/bin/chromium

WORKDIR /workspace

# Copy sandbox server and Remotion compositions
COPY package.json ./code/package.json
COPY sandbox-server.js ./code/sandbox-server.js
COPY remotion-compositions/ ./code/remotion-compositions/

# Install sandbox server dependencies (includes @remotion/bundler + renderer)
RUN cd /workspace/code && npm install

# Create workspace directory structure
RUN mkdir -p input/chunks input/audio \
    assets/memes assets/sfx assets/music \
    intermediate/subtitles intermediate/timeline intermediate/audio_mixed \
    output

# Install Remotion composition dependencies (bundler + renderer need full install)
RUN cd /workspace/code/remotion-compositions && npm install

EXPOSE 9876

CMD ["node", "/workspace/code/sandbox-server.js"]
