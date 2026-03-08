FROM n8nio/n8n:latest

USER root

# Install additional packages if needed
RUN apk add --update --no-cache \
    curl

USER node

# Expose port
EXPOSE 5678

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5678/healthz || exit 1

CMD ["n8n"]
