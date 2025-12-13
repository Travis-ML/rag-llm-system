from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx
import json
import time
from datetime import datetime
import os
import asyncio

app = FastAPI()

# Configuration from environment variables
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://rag-ollama:11434")
SPLUNK_HEC_URL = os.getenv("SPLUNK_HEC_URL", "")
SPLUNK_HEC_TOKEN = os.getenv("SPLUNK_HEC_TOKEN", "")
VERIFY_SSL = os.getenv("VERIFY_SSL", "false").lower() == "true"

# LOGGING TOGGLE - Currently REQUIRED for system to work properly
# TODO: Fix Open WebUI dependency on logging to make this truly optional
ENABLE_LOGGING = os.getenv("ENABLE_LOGGING", "true").lower() == "true"

async def send_to_hec(event_data: dict, retry: int = 3):
    """Send event to Splunk HEC - only if logging is enabled"""
    
    # Check if logging is enabled
    if not ENABLE_LOGGING:
        return
    
    if not SPLUNK_HEC_TOKEN or not SPLUNK_HEC_URL:
        print("Warning: Logging enabled but HEC credentials not configured")
        return
    
    # Format for HEC
    hec_event = {
        "time": time.time(),
        "sourcetype": "ollama:interactions:json",
        "source": "ollama_proxy",
        "host": "rag-system",
        "event": event_data
    }
    
    headers = {
        "Authorization": f"Splunk {SPLUNK_HEC_TOKEN}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(verify=VERIFY_SSL, timeout=10.0) as client:
        for attempt in range(retry):
            try:
                response = await client.post(
                    SPLUNK_HEC_URL,
                    json=hec_event,
                    headers=headers
                )
                
                if response.status_code == 200:
                    print(f"✓ Sent event to HEC: {event_data.get('model')} - {event_data.get('path')}")
                    return
                else:
                    print(f"✗ HEC error {response.status_code}: {response.text}")
                    
            except Exception as e:
                print(f"✗ HEC send failed (attempt {attempt+1}/{retry}): {e}")
                if attempt < retry - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

# IMPORTANT: Define specific routes BEFORE the wildcard route
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "logging_enabled": ENABLE_LOGGING,
        "hec_configured": bool(SPLUNK_HEC_TOKEN and SPLUNK_HEC_URL)
    }

@app.get("/config")
async def get_config():
    """View current configuration (without exposing secrets)"""
    return {
        "logging_enabled": ENABLE_LOGGING,
        "ollama_host": OLLAMA_HOST,
        "hec_url_configured": bool(SPLUNK_HEC_URL),
        "hec_token_configured": bool(SPLUNK_HEC_TOKEN),
        "ssl_verify": VERIFY_SSL
    }

# Wildcard route must come AFTER specific routes
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(request: Request, path: str):
    """Proxy all requests to Ollama and optionally log to Splunk HEC"""
    
    # Start timing
    start_time = time.time()
    timestamp = datetime.utcnow().isoformat()
    
    # Get request details
    url = f"{OLLAMA_HOST}/{path}"
    headers = dict(request.headers)
    headers.pop('host', None)
    
    # Get request body
    body = await request.body()
    request_json = None
    if body:
        try:
            request_json = json.loads(body)
        except:
            pass
    
    # Only build log entry if logging is enabled
    log_entry = None
    if ENABLE_LOGGING:
        log_entry = {
            "timestamp": timestamp,
            "event_type": "ollama_interaction",
            "method": request.method,
            "path": path,
            "client_ip": request.client.host if request.client else None
        }

        if request_json:
            log_entry["model"] = request_json.get("model")
            log_entry["stream"] = request_json.get("stream", False)

            # Handle /api/chat endpoint (uses messages array)
            if "messages" in request_json:
                messages = request_json.get("messages", [])
                log_entry["messages"] = messages  # Full conversation history
                log_entry["message_count"] = len(messages)

                # Extract the latest user message for quick reference
                if messages:
                    latest_user_msg = next((m for m in reversed(messages) if m.get("role") == "user"), None)
                    if latest_user_msg:
                        log_entry["latest_user_message"] = latest_user_msg.get("content", "")[:1000]

                # Extract system prompts
                system_msgs = [m.get("content") for m in messages if m.get("role") == "system"]
                if system_msgs:
                    log_entry["system_prompts"] = system_msgs

            # Handle /api/generate endpoint (uses prompt field)
            elif "prompt" in request_json:
                log_entry["prompt"] = request_json.get("prompt", "")[:2000]

            # Capture model parameters
            options = request_json.get("options", {})
            if options:
                log_entry["temperature"] = options.get("temperature")
                log_entry["top_p"] = options.get("top_p")
                log_entry["top_k"] = options.get("top_k")
                log_entry["num_ctx"] = options.get("num_ctx")
                log_entry["repeat_penalty"] = options.get("repeat_penalty")

            # Capture any tools/functions being used
            if "tools" in request_json:
                log_entry["tools"] = request_json.get("tools")

            # Capture format (json mode, etc)
            if "format" in request_json:
                log_entry["format"] = request_json.get("format")
    
    # Handle streaming vs non-streaming
    if request_json and request_json.get("stream"):
        # STREAMING: Create async generator that manages its own client
        full_response = ""
        last_chunk_data = {}

        async def stream_and_log():
            nonlocal full_response, last_chunk_data
            # Create client inside the generator to control its lifecycle
            async with httpx.AsyncClient(timeout=300.0) as client:
                try:
                    async with client.stream(
                        request.method,
                        url,
                        headers=headers,
                        content=body
                    ) as response:
                        async for chunk in response.aiter_bytes():
                            # Parse for logging (don't modify chunk)
                            if ENABLE_LOGGING:
                                try:
                                    line = chunk.decode('utf-8').strip()
                                    if line:
                                        data = json.loads(line)
                                        last_chunk_data = data  # Store last chunk for metadata

                                        # Handle chat API streaming (message.content)
                                        if "message" in data:
                                            full_response += data.get("message", {}).get("content", "")
                                        # Handle generate API streaming (response field)
                                        elif "response" in data:
                                            full_response += data.get("response", "")
                                except:
                                    pass
                            yield chunk

                finally:
                    # Log after streaming completes
                    if ENABLE_LOGGING and log_entry:
                        duration = time.time() - start_time
                        log_entry["assistant_response"] = full_response[:5000]
                        log_entry["response_length"] = len(full_response)
                        log_entry["duration_seconds"] = round(duration, 3)
                        log_entry["stream"] = True

                        # Extract metadata from last chunk
                        if last_chunk_data:
                            log_entry["done"] = last_chunk_data.get("done")
                            log_entry["total_duration_ns"] = last_chunk_data.get("total_duration")
                            log_entry["load_duration_ns"] = last_chunk_data.get("load_duration")
                            log_entry["prompt_eval_count"] = last_chunk_data.get("prompt_eval_count")
                            log_entry["prompt_eval_duration_ns"] = last_chunk_data.get("prompt_eval_duration")
                            log_entry["eval_count"] = last_chunk_data.get("eval_count")
                            log_entry["eval_duration_ns"] = last_chunk_data.get("eval_duration")

                            if log_entry.get("eval_count") and duration > 0:
                                log_entry["tokens_per_second"] = round(log_entry["eval_count"] / duration, 2)

                        asyncio.create_task(send_to_hec(log_entry))

        return StreamingResponse(
            stream_and_log(),
            media_type="application/x-ndjson"
        )
    
    else:
        # NON-STREAMING: Use context manager normally
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                response = await client.request(
                    request.method,
                    url,
                    headers=headers,
                    content=body
                )
                
                # Log non-streaming response
                if ENABLE_LOGGING and log_entry:
                    duration = time.time() - start_time

                    try:
                        response_json = response.json()

                        # Handle /api/chat response (has message field)
                        if "message" in response_json:
                            message = response_json.get("message", {})
                            log_entry["assistant_response"] = message.get("content", "")[:5000]
                            log_entry["assistant_role"] = message.get("role")

                            # Capture tool calls if present
                            if "tool_calls" in message:
                                log_entry["tool_calls"] = message.get("tool_calls")

                        # Handle /api/generate response (has response field)
                        elif "response" in response_json:
                            log_entry["assistant_response"] = response_json.get("response", "")[:5000]

                        # Capture performance metrics
                        log_entry["done"] = response_json.get("done")
                        log_entry["total_duration_ns"] = response_json.get("total_duration")
                        log_entry["load_duration_ns"] = response_json.get("load_duration")
                        log_entry["prompt_eval_count"] = response_json.get("prompt_eval_count")
                        log_entry["prompt_eval_duration_ns"] = response_json.get("prompt_eval_duration")
                        log_entry["eval_count"] = response_json.get("eval_count")
                        log_entry["eval_duration_ns"] = response_json.get("eval_duration")

                        # Calculate tokens per second
                        if log_entry.get("eval_count") and duration > 0:
                            log_entry["tokens_per_second"] = round(log_entry["eval_count"] / duration, 2)

                        # Capture context window info
                        if "context" in response_json:
                            log_entry["context_length"] = len(response_json.get("context", []))

                        # Store full response for analysis
                        log_entry["full_response_json"] = response_json

                    except Exception as e:
                        log_entry["assistant_response"] = response.text[:5000]
                        log_entry["parse_error"] = str(e)

                    log_entry["duration_seconds"] = round(duration, 3)
                    log_entry["status_code"] = response.status_code

                    asyncio.create_task(send_to_hec(log_entry))
                
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            
            except Exception as e:
                # Log errors
                if ENABLE_LOGGING and log_entry:
                    log_entry["error"] = str(e)
                    log_entry["duration_seconds"] = round(time.time() - start_time, 3)
                    asyncio.create_task(send_to_hec(log_entry))
                raise

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("Starting Ollama Logging Proxy...")
    print(f"Logging: {'ENABLED ✓' if ENABLE_LOGGING else 'DISABLED (default)'}")
    if ENABLE_LOGGING:
        print(f"HEC URL: {SPLUNK_HEC_URL}")
        print(f"HEC Token: {'Configured ✓' if SPLUNK_HEC_TOKEN else 'NOT CONFIGURED ✗'}")
        print(f"SSL Verify: {VERIFY_SSL}")
    else:
        print("To enable logging: Set ENABLE_LOGGING=true in .env")
    print(f"Proxying to: {OLLAMA_HOST}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=11435)