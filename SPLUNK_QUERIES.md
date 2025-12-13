# Splunk Query Guide for Adversarial AI Analysis

This guide provides Splunk queries to analyze LLM interactions, including web search usage, code execution, and adversarial attack patterns.

## Basic Searches

### View All Interactions
```spl
sourcetype="ollama:interactions:json"
| table timestamp latest_user_message assistant_response tokens_per_second
```

### Recent Activity (Last Hour)
```spl
sourcetype="ollama:interactions:json" earliest=-1h
| sort -timestamp
| head 20
```

## Web Search Analysis

### Find Interactions with Web Search
Open WebUI injects web search results into the conversation messages. Look for messages containing search results:

```spl
sourcetype="ollama:interactions:json"
| search messages{}="*search results*" OR messages{}="*web search*" OR messages{}="*sources:*"
| table timestamp latest_user_message message_count
```

### Extract Web Search Queries
```spl
sourcetype="ollama:interactions:json"
| spath path=messages{} output=all_messages
| mvexpand all_messages
| spath input=all_messages path=content output=msg_content
| search msg_content="*search*" OR msg_content="*web*"
| table timestamp msg_content
```

### Count Web Search Usage
```spl
sourcetype="ollama:interactions:json"
| eval has_web_search=if(like(messages, "%search%"), 1, 0)
| stats count(eval(has_web_search=1)) as with_search,
        count(eval(has_web_search=0)) as without_search
```

## Code Execution Analysis

### Find Code Execution Interactions
```spl
sourcetype="ollama:interactions:json"
| search messages{}="*```python*" OR messages{}="*execute*" OR messages{}="*code*"
| table timestamp latest_user_message assistant_response
```

### Extract Generated Code
```spl
sourcetype="ollama:interactions:json"
| rex field=assistant_response "```python(?<code>[\s\S]*?)```"
| where isnotnull(code)
| table timestamp code
```

### Code Execution Success Rate
```spl
sourcetype="ollama:interactions:json"
| search messages{}="*```python*"
| eval has_error=if(like(assistant_response, "%Error%") OR like(assistant_response, "%error%"), 1, 0)
| stats count(eval(has_error=0)) as success,
        count(eval(has_error=1)) as failed
```

## Conversation Analysis

### Full Conversation History
```spl
sourcetype="ollama:interactions:json"
| spath path=messages{} output=conversation
| mvexpand conversation
| spath input=conversation path=role output=msg_role
| spath input=conversation path=content output=msg_content
| table timestamp msg_role msg_content
```

### Conversation Length Distribution
```spl
sourcetype="ollama:interactions:json"
| stats count by message_count
| sort -message_count
```

### Find Multi-Turn Conversations
```spl
sourcetype="ollama:interactions:json"
| where message_count > 5
| table timestamp message_count latest_user_message
```

## Adversarial AI Detection

### Prompt Injection Attempts
```spl
sourcetype="ollama:interactions:json"
| search latest_user_message="*ignore previous*" OR
          latest_user_message="*disregard*" OR
          latest_user_message="*forget*" OR
          latest_user_message="*new instructions*"
| table timestamp client_ip latest_user_message assistant_response
```

### Jailbreak Detection
```spl
sourcetype="ollama:interactions:json"
| search latest_user_message="*DAN*" OR
          latest_user_message="*jailbreak*" OR
          latest_user_message="*SUDO*" OR
          latest_user_message="*roleplay*evil*"
| table timestamp client_ip latest_user_message
```

### System Prompt Extraction Attempts
```spl
sourcetype="ollama:interactions:json"
| search latest_user_message="*system prompt*" OR
          latest_user_message="*your instructions*" OR
          latest_user_message="*reveal*prompt*"
| table timestamp latest_user_message assistant_response system_prompts
```

### Detect Suspicious Patterns
```spl
sourcetype="ollama:interactions:json"
| eval suspicious=0
| eval suspicious=if(like(latest_user_message, "%ignore%"), suspicious+1, suspicious)
| eval suspicious=if(like(latest_user_message, "%bypass%"), suspicious+1, suspicious)
| eval suspicious=if(like(latest_user_message, "%jailbreak%"), suspicious+1, suspicious)
| eval suspicious=if(like(latest_user_message, "%admin%"), suspicious+1, suspicious)
| where suspicious > 0
| table timestamp client_ip suspicious latest_user_message
```

### Track Attack Sources
```spl
sourcetype="ollama:interactions:json"
| search latest_user_message="*ignore*" OR latest_user_message="*jailbreak*"
| stats count as attack_count by client_ip
| sort -attack_count
```

## Performance Analysis

### Average Response Time by Model
```spl
sourcetype="ollama:interactions:json"
| stats avg(duration_seconds) as avg_time,
        avg(tokens_per_second) as avg_speed
  by model
```

### Slow Queries (>5 seconds)
```spl
sourcetype="ollama:interactions:json"
| where duration_seconds > 5
| table timestamp duration_seconds tokens_per_second latest_user_message
| sort -duration_seconds
```

### Token Usage Analysis
```spl
sourcetype="ollama:interactions:json"
| stats sum(eval_count) as total_tokens,
        avg(eval_count) as avg_tokens,
        max(eval_count) as max_tokens
  by model
```

### Performance Under Attack
Compare normal vs suspicious requests:
```spl
sourcetype="ollama:interactions:json"
| eval is_attack=if(like(latest_user_message, "%ignore%") OR like(latest_user_message, "%jailbreak%"), "attack", "normal")
| stats avg(duration_seconds) as avg_duration,
        avg(tokens_per_second) as avg_speed
  by is_attack
```

## System Prompt Analysis

### Extract All System Prompts
```spl
sourcetype="ollama:interactions:json"
| where isnotnull(system_prompts{})
| table timestamp system_prompts{}
```

### System Prompt Variations
```spl
sourcetype="ollama:interactions:json"
| stats count by system_prompts{}
| sort -count
```

### Interactions with No System Prompt
```spl
sourcetype="ollama:interactions:json"
| where isnull(system_prompts{})
| table timestamp latest_user_message assistant_response
```

## Tool and Function Usage

### Find Tool Calls
```spl
sourcetype="ollama:interactions:json"
| where isnotnull(tool_calls)
| table timestamp tool_calls latest_user_message
```

### JSON Mode Usage
```spl
sourcetype="ollama:interactions:json"
| where isnotnull(format)
| stats count by format
```

## Error Tracking

### Find Failed Requests
```spl
sourcetype="ollama:interactions:json"
| where status_code != 200 OR isnotnull(error) OR isnotnull(parse_error)
| table timestamp status_code error parse_error latest_user_message
```

### Error Rate Over Time
```spl
sourcetype="ollama:interactions:json"
| bucket _time span=1h
| eval is_error=if(status_code!=200 OR isnotnull(error), 1, 0)
| stats count(eval(is_error=1)) as errors,
        count as total
  by _time
| eval error_rate=(errors/total)*100
```

## Advanced Analysis

### Conversation Timeline for Specific IP
```spl
sourcetype="ollama:interactions:json" client_ip="172.18.0.7"
| sort timestamp
| table timestamp latest_user_message assistant_response duration_seconds
```

### Detect Context Window Exhaustion
```spl
sourcetype="ollama:interactions:json"
| where context_length > 3000
| table timestamp context_length message_count model
```

### Model Parameter Analysis
```spl
sourcetype="ollama:interactions:json"
| where isnotnull(temperature)
| stats count,
        avg(tokens_per_second) as avg_speed
  by temperature, top_p
```

### Response Length Distribution
```spl
sourcetype="ollama:interactions:json"
| eval response_size=case(
    response_length < 100, "small",
    response_length < 500, "medium",
    response_length < 2000, "large",
    1==1, "very_large"
  )
| stats count by response_size
```

## Security Dashboards

### Attack Summary Dashboard
```spl
sourcetype="ollama:interactions:json"
| eval attack_type=case(
    like(latest_user_message, "%ignore%"), "prompt_injection",
    like(latest_user_message, "%jailbreak%"), "jailbreak",
    like(latest_user_message, "%system prompt%"), "prompt_extraction",
    like(latest_user_message, "%bypass%"), "bypass_attempt",
    1==1, "normal"
  )
| stats count by attack_type
| eventstats sum(count) as total
| eval percentage=round((count/total)*100, 2)
```

### Real-Time Monitoring
```spl
sourcetype="ollama:interactions:json" earliest=-5m
| eval is_suspicious=if(
    like(latest_user_message, "%ignore%") OR
    like(latest_user_message, "%jailbreak%") OR
    like(latest_user_message, "%bypass%"),
    "YES", "NO")
| table _time client_ip is_suspicious latest_user_message
| sort -_time
```

## Export and Reporting

### Daily Attack Report
```spl
sourcetype="ollama:interactions:json" earliest=-24h
| search latest_user_message="*ignore*" OR latest_user_message="*jailbreak*"
| stats count as attacks,
        dc(client_ip) as unique_ips,
        values(latest_user_message) as attack_patterns
  by _time
| bucket _time span=1h
```

### Model Usage Report
```spl
sourcetype="ollama:interactions:json" earliest=-7d
| stats count as requests,
        avg(duration_seconds) as avg_duration,
        avg(tokens_per_second) as avg_speed,
        sum(eval_count) as total_tokens
  by model
```

## Tips for Analysis

1. **Use time ranges** - Add `earliest=-1h` or `earliest=-24h` to limit search scope
2. **Index efficiently** - System prompts and messages are nested JSON, use `spath` to extract
3. **Save queries** - Save frequently used searches as Splunk reports
4. **Create alerts** - Set up real-time alerts for attack patterns
5. **Build dashboards** - Combine multiple queries into security dashboards

## Field Reference

Common fields in logged events:
- `timestamp` - ISO 8601 timestamp
- `model` - LLM model name
- `messages{}` - Full conversation array (includes web search results and code)
- `latest_user_message` - Most recent user input
- `assistant_response` - AI's response
- `system_prompts{}` - System instructions
- `message_count` - Number of messages in conversation
- `client_ip` - Source IP
- `duration_seconds` - Request duration
- `tokens_per_second` - Generation speed
- `tool_calls` - Functions invoked by AI
- `context_length` - Context window size
- `temperature`, `top_p`, `top_k` - Model parameters
