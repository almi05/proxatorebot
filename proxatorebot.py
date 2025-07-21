from telegram import (
    InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup,
    InlineKeyboardButton, Update, Message
)
from telegram.ext import (
    InlineQueryHandler, ApplicationBuilder, CommandHandler,
    ContextTypes, MessageHandler, CallbackQueryHandler, filters
)
from uuid import uuid4
import logging
import re
from urllib.parse import urlparse

BOT_TOKEN = 'ENTER_YOUR_TOKEN_HERE' # Remember to replace with your bot token from botfather!

# Istances provided to the bot
INSTANCES = [
    'https://proxatore.almi.eu.org/',
    'https://proxatore.octt.eu.org/',
    'https://laprovadialessioalmi.altervista.org/proxatore/index.php/'
]

# Supported domains, if not there, the bot will not provide any proxatore URL
ALLOWED_DOMAINS = [
    'bbs.spacc.eu.org', 'bilibili.com', 'bsky.app', 'facebook.com', 'm.facebook.com',
    'instagram.com', 'pinterest.com', 'raiplay.it', 'old.reddit.com', 'reddit.com',
    'open.spotify.com', 't.me', 'telegram.me', 'threads.net', 'threads.com', 'tiktok.com',
    'twitter.com', 'x.com', 'xiaohongshu.com', 'youtube.com', 'm.youtube.com',
    'vm.tiktok.com', 'youtu.be', 'altervista.org', 'blogspot.com', 'wordpress.com'
]

logging.basicConfig(level=logging.WARNING)

# --- URL Cleaning ---
def clean_url(url: str) -> str:
    url = re.sub(r'^https?://', '', url.strip())  # Removes http/https
    url = url.split('?')[0]  # Removes anything after ? to avoid platorms trakers
    return url

# --- Verify domain ---
def is_supported_domain(url: str) -> bool:
    try:
        parsed = urlparse(url if url.startswith('http') else 'https://' + url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return any(domain.endswith(allowed) for allowed in ALLOWED_DOMAINS)
    except:
        return False

def extract_domain(text: str) -> str | None:
    for domain in ALLOWED_DOMAINS:
        if domain in text:
            return domain
    return None

# --- /start command handler ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! This bot rewrites your social media URLs using Proxatore, so the media can easily be seen in Telegram.\n"
        "Try it by typing a URL inline (e.g., @ProxatoreBot https://...) in any chat, or just send a link here.\n"
        "Check /domains for supported sites."
    )

# --- /domains command handler ---
async def domains(update: Update, context: ContextTypes.DEFAULT_TYPE):
    domains_text = "\n".join(f"`{domain}`" for domain in ALLOWED_DOMAINS)
    await update.message.reply_text(f"Supported domains:\n\n{domains_text}", parse_mode='Markdown')

# --- inline query handler ---
async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()

    if not query.startswith("http"):
        for domain in ALLOWED_DOMAINS:
            if query.startswith(domain) or query.startswith("www." + domain):
                query = "https://" + query
                break

    if not re.match(r'^https?://', query):
        await update.inline_query.answer([
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Invalid link",
                description="Insert a valid link.",
                input_message_content=InputTextMessageContent("Insert a valid link."),
            )
        ], cache_time=1)
        return

    if not is_supported_domain(query):
        await update.inline_query.answer([
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="Unsupported link",
                description="This domain is not supported.",
                input_message_content=InputTextMessageContent("The domain is not supported by Proxatore."),
            )
        ], cache_time=1)
        return

    cleaned = clean_url(query)

    results = []
    for instance in INSTANCES:
        domain = re.sub(r'^https?://', '', instance.strip('/'))
        proxied_url = f"{instance}{cleaned}"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Open original", url="https://" + cleaned)]
        ])

        results.append(InlineQueryResultArticle(
            id=str(uuid4()),
            title=f"Open with {domain}",
            description=proxied_url,
            input_message_content=InputTextMessageContent(proxied_url),
            reply_markup=keyboard
        ))

    await update.inline_query.answer(results, cache_time=1)

# --- Private message ---
user_links = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not text.startswith("http"):
        for domain in ALLOWED_DOMAINS:
            if text.startswith(domain) or text.startswith("www." + domain):
                text = "https://" + text
                break

    if re.match(r'^https?://', text):
        if not is_supported_domain(text):
            await update.message.reply_text("This domain is not supported by Proxatore.")
            return

        cleaned = clean_url(text)
        user_links[update.effective_user.id] = (text, cleaned)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"Use {re.sub(r'^https?://', '', i.strip('/'))}", callback_data=i)]
            for i in INSTANCES
        ])
        await update.message.reply_text("Choose an instance:", reply_markup=keyboard)

    else:
        domain = extract_domain(text)
        if domain:
            reply = f"Proxied links for *{domain}*:\n\n"
            for instance in INSTANCES:
                url = f"{instance}{domain}"
                reply += f"• [Link]({url})\n"
            await update.message.reply_text(reply, parse_mode='Markdown', disable_web_page_preview=True)
        else:
            await update.message.reply_text("Insert a valid link.")

# --- Select istance buttons ---
async def handle_instance_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    instance = query.data
    user_id = update.effective_user.id

    if user_id not in user_links:
        await query.edit_message_text("Original URL not found.")
        return

    original, cleaned = user_links[user_id]
    proxied_url = f"{instance}{cleaned}"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Open original", url="https://" + cleaned)
        ]
    ])

    await query.edit_message_text(proxied_url, reply_markup=keyboard)

# --- MAIN ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("domains", domains))
    app.add_handler(InlineQueryHandler(inline_query_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(handle_instance_choice))
    app.run_polling()
