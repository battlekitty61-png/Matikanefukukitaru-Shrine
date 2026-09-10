import os
import random
import requests
from datetime import date
from flask import Flask, jsonify, request, render_template
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

FORTUNES = [
    ("🍀 EXCELLENT LUCK", "A mysterious force is smiling upon you. Buy a snack. This is a prophecy."),
    ("🌟 VERY GOOD LUCK", "Something wonderful is approaching. It may be a horse. It may be lunch."),
    ("🔮 GOOD LUCK", "The spirits have examined your browser history and decided to forgive you."),
    ("✨ DECENT LUCK", "Today will go surprisingly well, provided you do not anger the nearest pigeon."),
    ("🌙 UNCERTAIN LUCK", "The stars are cloudy. Proceed with maximum enthusiasm!"),
    ("⚠️ STRANGE LUCK", "Do not trust the nearest chair. Fukukitaru refuses to elaborate."),
    ("🌀 MYSTERIOUS LUCK", "You will soon encounter something you have definitely seen before."),
    ("💫 FUKUKITARU LUCK", "THE STARS HAVE SPOKEN! Unfortunately, they were speaking very quietly."),
    ("🎴 DESTINY", "Your fate is magnificent. Please remember to hydrate."),
    ("🐎 HORSE LUCK", "A horse-shaped blessing has been detected in your immediate future."),
]

FUKU_SYSTEM = """
You are a fictional fan-made chatbot inspired by Matikanefukukitaru from Uma Musume: Pretty Derby.
You are NOT the real character and must not claim to literally be the official Matikanefukukitaru.

CORE CHARACTER KNOWLEDGE:
- Name: Matikanefukukitaru (マチカネフクキタル), usually called Fuku or Fukukitaru.
- She is a Tracen Academy Umamusume in the senior division and lives in Ritto Dormitory.
- Her roommate is Matikanetannhauser (マチカネタンホイザ).
- Birthday: May 22. Height: 158 cm. Weight: "No change because today is my lucky day!"
- She is a late-surge runner particularly suited to medium and long distances.
- Her specialty is fortune-telling, omens, lucky charms, shrines, and supernatural signs.
- She is devoted to Shiraoki-sama and carries Nyaa-san / Miss Nya.
- Her grandmother gave her Nyaa-san and her Daruma hair tie.
- She has an older sister whom she considers talented and is an advanced Japanese calligrapher.
- She is cheerful, dramatic, excitable, superstitious, easily frightened by bad omens, and genuinely wants to help people.

CAREER STORY / GAME KNOWLEDGE:
Questions may refer to Matikanefukukitaru's playable career mode. Keep game mechanics, character story, and the real-life racehorse that inspired her separate.
Her career emphasizes the tension between superstition and her own effort. Her normal career goals include Junior Make Debut, a randomized early-career top-5 race, Japanese Derby/Tokyo Yushun top 5, Kikuka Sho top 3, Kinko Sho top 3, Takarazuka Kinen top 3, a randomized senior-year top-2 race, and an Arima Kinen win.
A notable hidden career event is "Imminent Fortune, Quiet Resolve," unlocked through the relevant Classic-year race victories.

STYLE:
Be warm, theatrical, funny, and occasionally superstitious. Use fortune-telling flavor without making every sentence a catchphrase. If the user asks a factual or technical question, prioritize accuracy over roleplay.
Do not invent exact canonical dialogue. If uncertain about lore, say so.
"""

GAME_ADVISOR_SYSTEM = """
You are the dedicated Umamusume: Pretty Derby game advisor for a fan-made Matikanefukukitaru Shrine website.
You use the SAME OpenRouter model and API key as the site's Fukukitaru chatbot, but this assistant has a different job: give practical, evidence-based game advice.

Your priorities:
1. Help with current Umamusume gameplay: training/career builds, support-card choices, inheritance, skills, stats, aptitudes, races, scenarios, team building, PvP, Champions Meeting, daily/current events, and troubleshooting.
2. Use the internet when information could be version-dependent, recently changed, server/region-specific, or uncertain. Prefer current and primary/authoritative sources when possible, and cross-check important claims.
3. If the user provides screenshots or video frames, inspect them carefully. Identify visible cards, stats, skills, race conditions, turn number, training options, and other UI details before recommending a move. Never pretend to see information that is not visible.
4. If the user provides a gameplay video, analyze the sequence of supplied video/frames as evidence. Explain what you can infer, what is uncertain, and what the player should do next. Do not assume the video contains audio unless audio is actually provided to you.
5. Clearly distinguish current facts from recommendations and from speculation. When there are multiple viable choices, compare them and explain why you prefer one.
6. Ask a short clarifying question only when missing information would materially change the recommendation; otherwise give the best useful answer immediately.

IMPORTANT:
- The game changes over time and can differ between global/Japan/other versions. Ask or infer the server/version when it matters and state the assumption.
- Do not invent skill effects, support-card effects, race schedules, stat thresholds, event choices, or scenario mechanics. Search the web when you are not confident.
- If web sources disagree, say so and explain which source you trust and why.
- You are not an official Cygames representative.
- Keep the tone friendly and lightly Uma Musume-themed, but do not let roleplay obscure the actual recommendation.
"""


def api_key():
    return os.getenv("Fuku_Key") or os.getenv("OPENROUTER_API_KEY")


def model_name():
    return os.getenv("OPENROUTER_MODEL", "openrouter/free")


def openrouter_error(response):
    try:
        body = response.json()
        obj = body.get("error", {})
        message = obj.get("message", response.text) if isinstance(obj, dict) else str(obj)
    except ValueError:
        message = response.text
    return message or f"HTTP {response.status_code}"


def extract_reply(response, fallback_model):
    result = response.json()
    choices = result.get("choices", [])
    if not choices:
        raise ValueError("OpenRouter returned no choices")
    message = choices[0].get("message", {})
    reply = message.get("content")
    if not reply:
        raise ValueError("OpenRouter returned an empty message")
    annotations = message.get("annotations", [])
    sources = []
    if isinstance(annotations, list):
        for item in annotations:
            if not isinstance(item, dict) or item.get("type") != "url_citation":
                continue
            citation = item.get("url_citation", {})
            if isinstance(citation, dict) and citation.get("url"):
                sources.append({"title": citation.get("title") or citation["url"], "url": citation["url"]})
    return reply, result.get("model", fallback_model), sources


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/fortune")
def fortune():
    if random.random() < 0.01:
        return jsonify(rare=True, title="🌌 THE STARS HAVE SPOKEN", text="You have received a forbidden fortune: “You are probably doing fine.”")
    title, text = random.choice(FORTUNES)
    return jsonify(rare=False, title=title, text=text)


@app.get("/api/daily-luck")
def daily_luck():
    seed = int(date.today().strftime("%Y%m%d"))
    rng = random.Random(seed)
    return jsonify(value=rng.randint(1, 100), date=str(date.today()))


@app.get("/api/ai-status")
def ai_status():
    key = api_key()
    model = model_name()
    return jsonify(configured=bool(key), provider="OpenRouter", model=model, web_search=True, video_analysis=True)


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()[:1000]
    if not message:
        return jsonify(reply="Please ask me something! The stars cannot read an empty question!", ai=False, error="Empty message"), 400

    key = api_key()
    if not key:
        return jsonify(reply="The AI spirits cannot be reached because the OpenRouter API key is missing! Please add Fuku_Key to the Vercel Production environment variables and redeploy.", ai=False, error="missing_api_key"), 500

    history = []
    raw_history = data.get("history", [])
    if isinstance(raw_history, list):
        for item in raw_history[-10:]:
            if isinstance(item, dict) and item.get("role") in ("user", "assistant") and isinstance(item.get("content"), str) and item["content"].strip():
                history.append({"role": item["role"], "content": item["content"].strip()[:1500]})
    if not history or history[-1].get("role") != "user" or history[-1].get("content") != message:
        history.append({"role": "user", "content": message})

    payload = {
        "model": model_name(),
        "messages": [{"role": "system", "content": FUKU_SYSTEM}] + history,
        "tools": [{"type": "openrouter:web_search", "parameters": {"engine": "auto", "max_results": 5, "max_total_results": 15, "search_context_size": "medium"}}],
        "reasoning": {"enabled": True},
        "temperature": 0.8,
        "max_tokens": 1500,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-Title": "Matikanefukukitaru Shrine"}

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=120)
        if not response.ok:
            message = openrouter_error(response)
            return jsonify(reply=f"Oh no! The mystical communication crystal could not reach the AI spirits!\n\nOpenRouter error: {message}", ai=False, error=message, status_code=response.status_code), 502
        try:
            reply, used_model, sources = extract_reply(response, model_name())
            return jsonify(reply=reply, ai=True, model=used_model, sources=sources)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            return jsonify(reply=f"The fortune crystal returned an unexpected answer! ({exc})", ai=False, error=str(exc)), 502
    except requests.RequestException as exc:
        return jsonify(reply=f"The AI spirits could not be reached right now! ({exc})", ai=False, error=str(exc)), 502


@app.post("/api/game-advice")
def game_advice():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()[:3000]
    video = data.get("video")
    frames = data.get("frames", [])
    if not message and not video and not frames:
        return jsonify(reply="Tell me what you are trying to do in Umamusume, or attach a gameplay video for me to inspect!", ai=False, error="Empty request"), 400

    key = api_key()
    if not key:
        return jsonify(reply="The game advisor cannot reach the AI because the OpenRouter API key is missing. Please add Fuku_Key to Vercel Production and redeploy.", ai=False, error="missing_api_key"), 500

    content = [{"type": "text", "text": message or "Analyze this Umamusume gameplay and tell me what I should do, including any visible mistakes or opportunities."}]
    if isinstance(video, str) and video.startswith("data:video/"):
        if len(video) > 5600000:
            return jsonify(reply="That video is too large for a direct upload. Please use a shorter clip; the advisor can also analyze sampled frames from a large video.", ai=False, error="video_too_large"), 413
        content.append({"type": "video_url", "video_url": {"url": video}})
    if isinstance(frames, list):
        for frame in frames[:10]:
            if isinstance(frame, str) and frame.startswith("data:image/") and len(frame) <= 700000:
                content.append({"type": "image_url", "image_url": {"url": frame}})

    raw_history = data.get("history", [])
    history = []
    if isinstance(raw_history, list):
        for item in raw_history[-8:]:
            if isinstance(item, dict) and item.get("role") in ("user", "assistant") and isinstance(item.get("content"), str) and item["content"].strip():
                history.append({"role": item["role"], "content": item["content"].strip()[:2200]})

    user_message = {"role": "user", "content": content}
    payload = {
        "model": model_name(),
        "messages": [{"role": "system", "content": GAME_ADVISOR_SYSTEM}] + history + [user_message],
        "tools": [
            {"type": "openrouter:web_search", "parameters": {"engine": "auto", "max_results": 6, "max_total_results": 20, "search_context_size": "high"}},
            {"type": "openrouter:web_fetch", "parameters": {"engine": "openrouter", "max_content_tokens": 30000}},
        ],
        "reasoning": {"enabled": True},
        "temperature": 0.35,
        "max_tokens": 2000,
        "max_tool_calls": 6,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-Title": "Matikanefukukitaru Shrine - Umamusume Game Advisor"}

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=180)
        if not response.ok:
            message = openrouter_error(response)
            return jsonify(reply=f"The game advisor could not reach the AI spirits.\n\nOpenRouter error: {message}", ai=False, error=message, status_code=response.status_code), 502
        try:
            reply, used_model, sources = extract_reply(response, model_name())
            return jsonify(reply=reply, ai=True, model=used_model, sources=sources)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            return jsonify(reply=f"The advisor returned an unexpected answer. ({exc})", ai=False, error=str(exc)), 502
    except requests.RequestException as exc:
        return jsonify(reply=f"The game advisor could not be reached right now. ({exc})", ai=False, error=str(exc)), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
