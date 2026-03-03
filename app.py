from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

YANDEX_GPT_KEY = os.environ.get('YANDEX_GPT_KEY')
YANDEX_FOLDER_ID = os.environ.get('YANDEX_FOLDER_ID')
YANDEX_MODEL_URI = os.environ.get(
    'YANDEX_MODEL_URI',
    'gpt://b1g5g2o9i44gp0v5p4qu/aliceai-llm/latest'
)

conversations = {}


# Главная страница
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "ok",
        "message": "Yandex AI Proxy работает"
    })


# Проверка здоровья сервиса
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


# Чтобы убрать 404 на favicon
@app.route('/favicon.ico')
def favicon():
    return ('', 204)


# Чат
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    user_id = data.get('user_id', 'default')
    message = data.get('message')

    if not message:
        return jsonify({"error": "Message is required"}), 400

    if user_id not in conversations:
        conversations[user_id] = []

    conversations[user_id].append({
        "role": "user",
        "text": message
    })

    payload = {
        "modelUri": YANDEX_MODEL_URI,
        "completionOptions": {
            "temperature": 0.6,
            "maxTokens": 2000
        },
        "messages": conversations[user_id]
    }

    headers = {
        "Authorization": f"Api-Key {YANDEX_GPT_KEY}",
        "x-folder-id": YANDEX_FOLDER_ID,
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        json=payload,
        headers=headers
    )

    if response.status_code != 200:
        return jsonify({
            "error": "Yandex API error",
            "details": response.text
        }), 500

    result = response.json()
    answer = result['result']['alternatives'][0]['message']['text']

    conversations[user_id].append({
        "role": "assistant",
        "text": answer
    })

    return jsonify({"answer": answer})


if __name__ == '__main__':
    # Локальный запуск
    app.run(host='0.0.0.0', port=8080)
