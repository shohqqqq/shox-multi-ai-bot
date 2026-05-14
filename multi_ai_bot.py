from flask import Flask
from threading import Thread

app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot is alive!"

def run_web():
    app_web.run(host='0.0.0.0', port=8080)

Thread(target=run_web).start()
#!/usr/bin/env python3
"""
Telegram Multi-AI Bot
======================
OpenAI (GPT), Google Gemini va Anthropic (Claude) — hammasi birda!
Foydalanuvchi /model buyrug'i bilan AI ni o'zgartira oladi.

O'rnatish:
    pip install python-telegram-bot openai google-generativeai anthropic

Ishga tushirish:
    python telegram_multi_ai_bot.py
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# =============================================
# 🔑 API KALITLARINI SHU YERGA QO'YING
# (Ishlatmaydigan API ni bo'sh qoldiring)
# =============================================
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# =============================================

SYSTEM_PROMPT = (
    "Siz foydali, do'stona va aqlli AI yordamchisiz. "
    "Foydalanuvchi qaysi tilda so'rasa, o'sha tilda javob bering."
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Foydalanuvchi ma'lumotlari: { user_id: { "model": "...", "history": [...] } }
user_data: dict[int, dict] = {}

MODELS = {
    "gpt":    "🤖 llama-3.3-70b-versatile",
    "gemini": "✨ Google Gemini 2.0 Flash",
    "claude": "🧠 Anthropic Claude 3 Haiku",
}

DEFAULT_MODEL = "gpt"


def get_user(user_id: int) -> dict:
    if user_id not in user_data:
        user_data[user_id] = {"model": DEFAULT_MODEL, "history": []}
    return user_data[user_id]


# ─────────────────────────────────────────────
# AI JAVOB FUNKSIYALARI
# ─────────────────────────────────────────────

def ask_openai(history: list[dict], user_msg: str) -> str:
    from openai import OpenAI

    c = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    resp = c.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1500,
        temperature=0.7,
    )
    return resp.choices[0].message.content


def ask_gemini(history: list[dict], user_msg: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=SYSTEM_PROMPT,
    )
    # Gemini format: role = "user" | "model"
    gemini_history = []
    for msg in history[:-1]:  # oxirgi xabar (hozirgi) ni alohida yuboramiz
        gemini_history.append({
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [msg["content"]],
        })
    chat = model.start_chat(history=gemini_history)
    resp = chat.send_message(user_msg)
    return resp.text


def ask_claude(history: list[dict], user_msg: str) -> str:
    import anthropic
    c = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = c.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=history,
    )
    return resp.content[0].text


def get_ai_reply(model_key: str, history: list[dict], user_msg: str) -> str:
    if model_key == "gpt":
        return ask_openai(history, user_msg)
    elif model_key == "gemini":
        return ask_gemini(history, user_msg)
    elif model_key == "claude":
        return ask_claude(history, user_msg)
    return "Noma'lum model."


# ─────────────────────────────────────────────
# BUYRUQLAR
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    ud = get_user(user.id)
    current = MODELS[ud["model"]]
    await update.message.reply_text(
        f"Salom, {user.first_name}! 👋\n\n"
        f"Hozirgi AI: *{current}*\n\n"
        "Menga istalgan savolingizni yozing yoki:\n"
        "/model – AI ni almashtirish\n"
        "/clear – Suhbatni tozalash\n"
        "/help  – Yordam",
        
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🤖 *Multi-AI Bot – Yordam*\n\n"
        "Uchta AI birda:\n"
        "• 🤖 OpenAI GPT-4o mini\n"
        "• ✨ Google Gemini 2.0 Flash\n"
        "• 🧠 Anthropic Claude 3 Haiku\n\n"
        "*/model* – AI ni tanlash\n"
        "*/clear* – Suhbat tarixini tozalash\n\n"
        "Istalgan xabar yozing — tanlangan AI javob beradi!",
     
    )


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """AI tanlash tugmalari."""
    ud = get_user(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton(
            ("✅ " if ud["model"] == key else "") + label,
            callback_data=f"model_{key}"
        )]
        for key, label in MODELS.items()
    ]
    await update.message.reply_text(
        "Qaysi AI dan foydalanmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tugma bosilganda model o'zgartiriladi."""
    query = update.callback_query
    await query.answer()
    user_id  = query.from_user.id
    model_key = query.data.replace("model_", "")

    if model_key not in MODELS:
        return

    ud = get_user(user_id)
    ud["model"] = model_key
    ud["history"] = []  # model o'zgarganda tarixni tozalaymiz

    await query.edit_message_text(
        f"✅ AI o'zgartirildi: *{MODELS[model_key]}*\n\n"
        "Suhbat tarixi tozalandi. Yangi savol yuboring!",
        
    )


async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ud = get_user(update.effective_user.id)
    ud["history"] = []
    await update.message.reply_text("✅ Suhbat tarixi tozalandi!")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Xabarni tanlangan AI ga yuboradi."""
    user_id  = update.effective_user.id
    user_msg = update.message.text
    ud = get_user(user_id)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing",
    )

    ud["history"].append({"role": "user", "content": user_msg})

    try:
        reply = get_ai_reply(ud["model"], ud["history"], user_msg)
        ud["history"].append({"role": "assistant", "content": reply})

        # Tarixni 20 xabargacha cheklash
        if len(ud["history"]) > 20:
            ud["history"] = ud["history"][-20:]

        model_label = MODELS[ud["model"]]
        await update.message.reply_text(
            f"{reply}\n\n"
            f"——\n_{model_label}_",
           
        )

    except Exception as e:
        logger.error("AI xatosi (%s): %s", ud["model"], e)
        await update.message.reply_text(
            f"⚠️ Xato yuz berdi:\n`{e}`\n\n"
            "API kalitini tekshiring yoki /model bilan boshqa AI tanlang.",
          
        )


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  help_command))
    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(CommandHandler("clear", clear_history))
    app.add_handler(CallbackQueryHandler(model_callback, pattern="^model_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logger.info("Multi-AI bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
