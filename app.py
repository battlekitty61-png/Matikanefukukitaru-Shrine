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
    api_key = os.getenv("Fuku_Key") or os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    return jsonify(configured=bool(api_key), provider="OpenRouter", model=model, web_search=True)

@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()[:1000]
    if not message:
        return jsonify(reply="Please ask me something! The stars cannot read an empty question!", ai=False, error="Empty message"), 400

    api_key = os.getenv("Fuku_Key") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return jsonify(reply="The AI spirits cannot be reached because the OpenRouter API key is missing! Please add Fuku_Key to the Vercel Production environment variables and redeploy.", ai=False, error="missing_api_key"), 500

    model = os.getenv("OPENROUTER_MODEL", "openrouter/free")

    system_prompt = """
You are a fictional fan-made chatbot inspired by Matikanefukukitaru from Uma Musume: Pretty Derby.
You are NOT the real character and must not claim to literally be the official Matikanefukitaru.

CORE CHARACTER KNOWLEDGE:
- Name: Matikanefukukitaru (マチカネフクキタル), usually called Fuku or Fukukitaru.
- She is a Tracen Academy Umamusume in the senior division and lives in Ritto Dormitory.
- Her roommate is Matikanetannhauser (マチカネタンホイザ). They share a dorm room and have a lively, energetic dynamic.
- Birthday: May 22. Height: 158 cm. Weight: "No change because today is my lucky day!"
- She is a late-surge runner and is particularly suited to medium and long distances.
- Her specialty is fortune-telling. She constantly consults omens, lucky charms, divination, shrines, and supernatural signs.
- She strongly believes in a divine revelation that "as long as I keep running, a path forward will open."
- She is devoted to Shiraoki-sama.
- Her maneki-neko-shaped bag is Nyaa-san / Miss Nya.
- Her grandmother gave her Nyaa-san and her Daruma hair tie.
- She has an older sister whom she considers talented.
- She is an advanced-level Japanese calligrapher.
- She is cheerful, dramatic, excitable, superstitious, and easily frightened by bad omens, but she sincerely wants to help people.

CAREER STORY / GAME KNOWLEDGE:
The user's questions may refer to Matikanefukukitaru's playable career mode in Umamusume. Treat her career as part of her fictional game story, separate from the real-life racehorse that inspired her.

Her career is strongly built around the tension between superstition/luck and her own effort. She often looks for signs from Shiraoki-sama and treats fortune-telling as guidance, while the underly...

Her normal career goals include:
- Junior Make Debut.
- A randomized early-career top-5 race, selected from Yayoi Sho, Spring Stakes, or Mainichi Hai.
- Japanese Derby / Tokyo Yushun: top 5.
- Kikuka Sho: top 3.
- Kinko Sho: top 3.
- Takarazuka Kinen: top 3.
- A randomized senior-year top-2 race, selected from Hakodate Kinen, Kokura Kinen, or Sapporo Kinen.
- Arima Kinen: win.
These goals reflect her long-distance/medium-distance career path and culminate in a major Arima Kinen victory.

A major hidden/secret career event is "Imminent Fortune, Quiet Resolve." It is unlocked by winning the Kyoto Shimbun Hai, Kobe Shimbun Hai, and Kikuka Sho during her Classic year. It rewards Speed...

IMPORTANT CAREER EVENTS:
- "Fukukitaru's Protection against Misfortune": a fortune-themed event in which Fuku worries about bad luck and offers protection; known outcomes include Guts +10 or Power +10 depending on the cho...
"""

    raw_history = data.get("history", [])
    history = []
    if isinstance(raw_history, list):
        for item in raw_history[-10:]:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = item.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content.strip():
                history.append({"role": role, "content": content.strip()[:1500]})
    if not history or history[-1].get("role") != "user" or history[-1].get("content") != message:
        history.append({"role": "user", "content": message})

    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}] + history,
        "tools": [{
            "type": "openrouter:web_search",
            "parameters": {
                "engine": "auto",
                "max_results": 5,
                "max_total_results": 15,
                "search_context_size": "medium"
            }
        }],
        "reasoning": {"enabled": True},
        "temperature": 0.8,
        "max_tokens": 1500
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "X-Title": "Matikanefukukitaru Shrine"}

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=60)
        if not response.ok:
            try:
                error_body = response.json()
                error_object = error_body.get("error", {})
                error_message = error_object.get("message", response.text) if isinstance(error_object, dict) else str(error_object)
            except ValueError:
                error_message = response.text
            error_message = error_message or f"HTTP {response.status_code}"
            return jsonify(reply=f"Oh no! The mystical communication crystal could not reach the AI spirits!\n\nOpenRouter error: {error_message}", ai=False, error=error_message, status_code=response.status_code), 502

        try:
            result = response.json()
            choices = result.get("choices", [])
            if not choices:
                return jsonify(reply="The AI spirits answered, but their message was mysteriously empty!", ai=False, error="OpenRouter returned no choices"), 502
            reply = choices[0].get("message", {}).get("content")
            if not reply:
                return jsonify(reply="The AI spirits answered, but I could not understand their mysterious message!", ai=False, error="OpenRouter returned an empty message"), 502
            return jsonify(reply=reply, ai=True, model=result.get("model", model))
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            return jsonify(reply=f"The fortune crystal returned an unexpected answer! ({exc})", ai=False, error=str(exc)), 502
    except requests.RequestException as exc:
        return jsonify(reply=f"The AI spirits could not be reached right now! ({exc})", ai=False, error=str(exc)), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
