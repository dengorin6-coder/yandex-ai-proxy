from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# --- ENV ---
YANDEX_GPT_KEY = os.environ.get("YANDEX_GPT_KEY")
YANDEX_FOLDER_ID = os.environ.get("YANDEX_FOLDER_ID")
YANDEX_MODEL_URI = os.environ.get(
    "YANDEX_MODEL_URI",
    "gpt://b1g5g2o9i44gp0v5p4qu/aliceai-llm/latest",
)

# Секрет для доступа к твоему прокси (защита)
PROXY_SECRET = os.environ.get("PROXY_SECRET")  # добавь в Render -> Environment

conversations = {}


def require_api_key():
    """
    Простая защита: клиент должен прислать заголовок:
    X-API-KEY: <PROXY_SECRET>
    """
    # Если PROXY_SECRET не задан, лучше сразу падать — так безопаснее
    if not PROXY_SECRET:
        return jsonify({"error": "Server misconfigured: PROXY_SECRET is not set"}), 500

    client_key = request.headers.get("X-API-KEY")
    if client_key != PROXY_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    return None  # ok


def ensure_yandex_env():
    if not YANDEX_GPT_KEY or not YANDEX_FOLDER_ID or not YANDEX_MODEL_URI:
        return (
            jsonify(
                {
                    "error": "Server misconfigured: Yandex env vars missing",
                    "has_key": bool(YANDEX_GPT_KEY),
                    "has_folder": bool(YANDEX_FOLDER_ID),
                    "has_model_uri": bool(YANDEX_MODEL_URI),
                }
            ),
            500,
        )
    return None


# Главная страница
@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "ok", "message": "Yandex AI Proxy работает"})


# Проверка здоровья сервиса (без ключа)
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# Чтобы убрать 404 на favicon
@app.route("/favicon.ico")
def favicon():
    return ("", 204)


# Чат (тут защита включена)
@app.route("/chat", methods=["POST"])
def chat():
    # 1) Проверка доступа
    auth_err = require_api_key()
    if auth_err:
        return auth_err

    # 2) Проверка env для Яндекса
    y_err = ensure_yandex_env()
    if y_err:
        return y_err

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    user_id = data.get("user_id", "default")
    message = data.get("message")

    if not message:
        return jsonify({"error": "Message is required"}), 400

    if user_id not in conversations:
        conversations[user_id] = []

    conversations[user_id].append({"role": "user", "text": message})

    payload = {
        "modelUri": YANDEX_MODEL_URI,
        "completionOptions": {"temperature": 0.6, "maxTokens": 2000},
        "messages": conversations[user_id],
    }

    headers = {
        "Authorization": f"Api-Key {YANDEX_GPT_KEY}",
        "x-folder-id": YANDEX_FOLDER_ID,
        "Content-Type": "application/json",
    }

    response = requests.post(
        "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
        json=payload,
        headers=headers,
        timeout=60,
    )

    if response.status_code != 200:
        return jsonify({"error": "Yandex API error", "details": response.text}), 500

    result = response.json()
    answer = result["result"]["alternatives"][0]["message"]["text"]

    conversations[user_id].append({"role": "assistant", "text": answer})

    return jsonify({"answer": answer})


if __name__ == "__main__":
    # Локальный запуск
    app.run(host="0.0.0.0", port=8080)
