FROM node:20-slim

# Install system dependencies: FFmpeg + Python 3.11
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Remotion CLI globally
RUN npm install -g @remotion/cli remotion

WORKDIR /workspace

# Copy sandbox server and Remotion compositions
COPY package.json ./code/package.json
COPY sandbox-server.js ./code/sandbox-server.js
COPY remotion-compositions/ ./code/remotion-compositions/

# Install sandbox server dependencies
RUN cd /workspace/code && npm install --production

# Create workspace directory structure
RUN mkdir -p input/chunks input/audio \
    assets/memes assets/sfx assets/music \
    intermediate/subtitles intermediate/timeline intermediate/audio_mixed \
    output \
    code/remotion-compositions

# Install Remotion composition dependencies
RUN cd /workspace/code/remotion-compositions && \
    npm install --production 2>/dev/null || true

EXPOSE 9876

CMD ["node", "/workspace/code/sandbox-server.js"]
