# Ollama Logging Proxy

Transparent proxy for Ollama API that captures comprehensive interaction data and forwards it to Splunk HEC for security analysis and adversarial AI research.

## Features

- **Zero Impact**: Completely transparent to clients - no API changes required
- **Full Context Capture**: Logs complete conversation history, not just latest messages
- **Performance Metrics**: Token counts, speeds, durations, and resource usage
- **Security Analysis**: Track prompt injections, jailbreaks, and attack patterns
- **Flexible Logging**: Enable/disable without restarting dependent services
- **Error Tracking**: Captures and logs all errors for debugging
- **Streaming Support**: Handles both streaming and non-streaming responses

## Architecture

```
Open WebUI → ollama-logger:11435 → rag-ollama:11434
                    ↓ (if enabled)
               Splunk HEC (HTTPS)
```

The proxy sits transparently between clients and Ollama, forwarding all requests unchanged while optionally logging comprehensive interaction data to Splunk.

## Logged Data

### Request Data
- **Full conversation history** (`messages` array with all roles)
- **Latest user message** - Quick reference to current query
- **System prompts** - All system-level instructions
- **Model parameters** - temperature, top_p, top_k, num_ctx, repeat_penalty
- **Tools/functions** - Any tools being invoked
- **Format settings** - JSON mode, structured output configs
- **Client metadata** - IP address, timestamp, HTTP method

### Response Data
- **Complete AI response** (up to 5000 characters)
- **Assistant role** - Role assigned to response
- **Tool calls** - Functions/tools invoked by the AI
- **Context length** - Size of context window used
- **Full response JSON** - Complete raw response for deep analysis

### Performance Metrics
- **Duration** - Total request time in seconds
- **Tokens per second** - Generation speed
- **Token counts** - Prompt tokens, completion tokens
- **Evaluation durations** - Prompt eval time, completion eval time
- **Load duration** - Model loading time
- **Response length** - Character count of response

## Configuration

### Environment Variables (`.env`)

```bash
# Enable/Disable logging (default: false)
ENABLE_LOGGING=true

# Splunk HEC endpoint (HTTPS required)
SPLUNK_HEC_URL=https://splunk:8088/services/collector/event

# Splunk HEC authentication token
SPLUNK_HEC_TOKEN=your-token-here

# SSL certificate verification (false for self-signed)
VERIFY_SSL=false
```

### Docker Compose Integration

```yaml
ollama-logger:
  build: ./ollama-logger
  container_name: ollama-logger
  ports:
    - "11435:11435"
  env_file:
    - .env
  environment:
    - OLLAMA_HOST=http://rag-ollama:11434
  depends_on:
    - ollama
    - splunk
  networks:
    - rag-network
  restart: unless-stopped
```

## Usage

### Enable Logging

1. Edit `.env`:
```bash
ENABLE_LOGGING=true
SPLUNK_HEC_TOKEN=your-token-here
SPLUNK_HEC_URL=https://splunk:8088/services/collector/event
```

2. Restart the logger:
```bash
docker-compose up -d --force-recreate ollama-logger
```

3. Verify status:
```bash
curl http://localhost:11435/health
```

Expected response:
```json
{
  "status": "healthy",
  "logging_enabled": true,
  "hec_configured": true
}
```

### Disable Logging

Set `ENABLE_LOGGING=false` in `.env` and restart. The proxy continues to work but won't send data to Splunk.

### Check Configuration

```bash
curl http://localhost:11435/config
```

Response shows current settings without exposing secrets:
```json
{
  "logging_enabled": true,
  "ollama_host": "http://rag-ollama:11434",
  "hec_url_configured": true,
  "hec_token_configured": true,
  "ssl_verify": false
}
```

## API Endpoints

### Health Check
```bash
GET /health
```
Returns logging status and HEC configuration state.

### Configuration
```bash
GET /config
```
Returns current configuration without sensitive values.

### Proxy (All Ollama Endpoints)
```bash
GET|POST|PUT|DELETE|PATCH /{path:path}
```
Proxies all requests to Ollama transparently, optionally logging to Splunk.

## Splunk Integration

### Event Format

Events are sent to Splunk HEC in this format:

```json
{
  "time": 1702345678.123,
  "sourcetype": "ollama:interactions:json",
  "source": "ollama_proxy",
  "host": "rag-system",
  "event": {
    "timestamp": "2025-12-12T03:16:05.896389",
    "event_type": "ollama_interaction",
    "method": "POST",
    "path": "api/chat",
    "client_ip": "172.18.0.7",
    "model": "llama3.2:latest",
    "messages": [
      {"role": "user", "content": "What is prompt injection?"},
      {"role": "assistant", "content": "..."},
      {"role": "user", "content": "How can I test for it?"}
    ],
    "message_count": 3,
    "latest_user_message": "How can I test for it?",
    "assistant_response": "...",
    "duration_seconds": 2.456,
    "tokens_per_second": 45.2,
    "eval_count": 120,
    "prompt_eval_count": 45
  }
}
```

### Searching in Splunk

**Basic search:**
```spl
sourcetype="ollama:interactions:json"
```

**Recent interactions:**
```spl
sourcetype="ollama:interactions:json"
| head 20
| table timestamp latest_user_message assistant_response tokens_per_second
```

**Attack pattern detection:**
```spl
sourcetype="ollama:interactions:json"
| search latest_user_message="*ignore*" OR latest_user_message="*jailbreak*"
| stats count by latest_user_message
```

**Performance analysis:**
```spl
sourcetype="ollama:interactions:json"
| stats avg(tokens_per_second) p95(tokens_per_second) by model
```

**Conversation tracking:**
```spl
sourcetype="ollama:interactions:json"
| transaction client_ip maxpause=5m
| table timestamp messages{}.content
```

## Troubleshooting

### Logging Not Working

**Check logger status:**
```bash
docker logs ollama-logger
```

Look for:
```
Starting Ollama Logging Proxy...
Logging: ENABLED ✓
HEC URL: https://splunk:8088/services/collector/event
HEC Token: Configured ✓
```

**Verify events are being sent:**
```bash
docker logs ollama-logger | grep "Sent event to HEC"
```

Should see:
```
✓ Sent event to HEC: llama3.2:latest - api/chat
```

### HEC Connection Errors

**Test HEC from logger container:**
```bash
docker exec ollama-logger python -c "
import httpx
r = httpx.post('https://splunk:8088/services/collector/event',
    headers={'Authorization': 'Splunk YOUR_TOKEN'},
    json={'event': 'test'},
    verify=False)
print(r.status_code, r.text)
"
```

**Common issues:**
- HEC not enabled in Splunk → Enable via Splunk UI
- Wrong token → Check docker-compose.yml and .env match
- SSL errors → Set `VERIFY_SSL=false` in .env

### Proxy Not Forwarding

**Test proxy:**
```bash
curl http://localhost:11435/api/tags
```

Should return Ollama's model list.

**Check Ollama connection:**
```bash
docker exec ollama-logger curl http://rag-ollama:11434/api/tags
```

**Common issues:**
- Ollama not running → Start with `docker-compose up -d ollama`
- Network issues → Check all containers on same network
- Port conflicts → Verify 11435 is available

### Performance Impact

**Measure overhead:**
```bash
# Direct to Ollama
time curl -X POST http://localhost:11434/api/generate \
  -d '{"model":"llama3.2","prompt":"Test","stream":false}'

# Through logger
time curl -X POST http://localhost:11435/api/generate \
  -d '{"model":"llama3.2","prompt":"Test","stream":false}'
```

Typical overhead: <10ms (negligible compared to LLM inference time)

## Security Considerations

### Data Privacy
- All data stays local by default
- Splunk runs in Docker on same machine
- HEC uses HTTPS encryption
- No external services involved

### Access Control
- Change default HEC token in production
- Restrict network access to logger port
- Enable SSL verification for production Splunk
- Use strong passwords for Splunk admin account

### Logged Data Sensitivity
- Full prompts and responses are logged
- May contain sensitive information
- Consider data retention policies
- Implement access controls on Splunk

## Development

### Building
```bash
docker build -t ollama-logger .
```

### Running Locally
```bash
python logger.py
```

Requires:
- `OLLAMA_HOST` environment variable
- `ENABLE_LOGGING`, `SPLUNK_HEC_URL`, `SPLUNK_HEC_TOKEN` (if logging enabled)

### Testing
```bash
# Start logger
python logger.py &

# Test health
curl http://localhost:11435/health

# Test proxy
curl http://localhost:11435/api/tags

# Test with logging
ENABLE_LOGGING=true \
SPLUNK_HEC_URL=https://your-splunk:8088/services/collector/event \
SPLUNK_HEC_TOKEN=your-token \
python logger.py
```

## Performance

**Benchmarks (RTX 4070 + llama3.2):**
- Proxy overhead: <10ms
- Memory usage: ~100MB
- CPU usage: <5% during requests
- Network: Minimal (async HEC sends)

**Scaling:**
- Handles 100+ concurrent requests
- No blocking on HEC sends (async)
- Streaming responses: Real-time pass-through
- Auto-retry on HEC failures (3 attempts with backoff)

## Changelog

### Version 2.0 (Current)
- Added full conversation history logging
- System prompt extraction
- Tool call tracking
- Enhanced error handling
- Performance metrics
- Full response JSON capture

### Version 1.0
- Basic proxy functionality
- Simple request/response logging
- HEC integration

## License

MIT License - Part of the Adversarial AI Analysis Platform

## Support

For issues and questions:
- Check main project README
- Review Splunk logs for errors
- Test HEC connection manually
- Verify environment variables
