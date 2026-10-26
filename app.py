"""MOS 1 / MOSS starter cloud API.

IMPORTANT: Android application endpoint and response schema have not been verified.
"""
import hmac
import os
from urllib import error, request
import json
from flask import Flask, jsonify, request as flask_request

app = Flask(__name__)

@app.get('/')
@app.get('/health')
def health():
    return jsonify(status='ok', service='MOS 1 MOSS server')

@app.post('/chat')
def chat():
    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    shared_token = os.getenv('MOSS_ACCESS_TOKEN', '').strip()
    if not api_key or not shared_token:
        return jsonify(error='Server credentials are not configured'), 503
    supplied = flask_request.headers.get('X-MOSS-Token', '')
    if not hmac.compare_digest(supplied, shared_token):
        return jsonify(error='Unauthorized'), 401
    payload = flask_request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error='Expected JSON object'), 400
    message = payload.get('message')
    if not isinstance(message, str) or not message.strip():
        return jsonify(error='message is required'), 400
    if len(message) > 4000:
        return jsonify(error='message too long'), 413
    body = json.dumps({
        'model': os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'),
        'messages': [
            {'role': 'system', 'content': 'You are MOSS, a helpful assistant. Reply in Turkish unless requested otherwise.'},
            {'role': 'user', 'content': message.strip()}
        ],
        'max_completion_tokens': 700
    }).encode('utf-8')
    req = request.Request('https://api.openai.com/v1/chat/completions', data=body,
                          headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}, method='POST')
    try:
        with request.urlopen(req, timeout=35) as resp:
            response_json = json.load(resp)
        reply = response_json['choices'][0]['message']['content']
        return jsonify(reply=reply)
    except error.HTTPError as exc:
        # Do not expose credentials or raw provider error body to clients.
        app.logger.warning('Provider returned HTTP %s', exc.code)
        return jsonify(error='AI provider request failed', status=exc.code), 502
    except (error.URLError, TimeoutError, ValueError, KeyError, IndexError) as exc:
        app.logger.warning('AI provider request failed: %s', type(exc).__name__)
        return jsonify(error='AI provider unavailable'), 502

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '10000')))
