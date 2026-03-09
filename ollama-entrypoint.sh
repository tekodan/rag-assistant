#!/bin/sh
set -e

EMBED_MODEL=${EMBED_MODEL:-nomic-embed-text}
CHAT_MODEL=${CHAT_MODEL:-llama3.2:1b}

# Start ollama in background
ollama serve &
OLLAMA_PID=$!

# Wait until ready
echo "Waiting for Ollama to start..."
until ollama list > /dev/null 2>&1; do
  sleep 1
done

# Pull models if not already present
for MODEL in "$EMBED_MODEL" "$CHAT_MODEL"; do
  if ollama list | grep -q "^$MODEL"; then
    echo "Model $MODEL already present, skipping."
  else
    echo "Pulling $MODEL..."
    ollama pull "$MODEL"
  fi
done

echo "Ollama ready with models: $EMBED_MODEL, $CHAT_MODEL"
wait $OLLAMA_PID
