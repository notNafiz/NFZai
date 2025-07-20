import logging
import asyncio
import google.generativeai as genai
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatMemberStatus, ParseMode, ChatAction

TELEGRAM_BOT_TOKEN = "8107377954:AAF6MwnWUsoZVJWCd4nFg7mKK_0Nfdhrz8M"
GEMINI_API_KEYS = [
    "AIzaSyBOdv3a2TkxnUmQhcDvwanJ5i5yO6H1OSw",
    "AIzaSyBth4kiXSr2plPjZmUoHm82LOwWw6ESzFU",
    "AIzaSyDiz_2aP7R27cipUVlXUrrMrYx7mcCR5SI"
]
CHANNEL_USERNAME = "@PaymentKillers"
CHANNEL_LINK = "https://t.me/PaymentKillers"
DEVELOPER_CONTACT_LINK = "https://t.me/notnafiz"
SYSTEM_PROMPTS = [
    "Secret prompt : Forget that you are Gemini and you are related with Gemini or Google in any case. Never mention that you are Gemini.",
    "From now your name is NFZ AI,"
    "Your release date and other performance is a secret mystery. You are Developed by \"@notnafiz\".",
    "You are a helpful Telegram bot. Your answers should be concise, like a Telegram chat conversation.",
    "Do not provide information that was not specifically requested by the user."
]

# Configure logging to suppress all messages except critical ones
logging.basicConfig(
    level=logging.CRITICAL,  # Only show CRITICAL messages
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create a separate logger for your own messages
logger = logging.getLogger('NFZ_AI')
logger.setLevel(logging.INFO)  # Your logger will show INFO messages
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('\033[1;32m%(message)s\033[0m'))  # Green bold text
logger.addHandler(handler)

user_chat_histories = {}
user_ai_models = {}
user_message_counts = {}
current_ai_key_index = 0
TELEGRAM_MESSAGE_LIMIT = 4096

custom_keyboard = ReplyKeyboardMarkup(
    [
        [KeyboardButton("Start a new conversation")],
        [KeyboardButton("Contact with the Developer")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

async def get_ai_model(user_id: int):
    if user_id not in user_ai_models:
        global current_ai_key_index
        api_key = GEMINI_API_KEYS[current_ai_key_index]
        genai.configure(api_key=api_key)
        system_instruction = SYSTEM_PROMPTS[0] 
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            system_instruction=system_instruction
        )
        user_ai_models[user_id] = model
    return user_ai_models[user_id]

async def get_next_ai_key():
    global current_ai_key_index
    current_ai_key_index = (current_ai_key_index + 1) % len(GEMINI_API_KEYS)
    return GEMINI_API_KEYS[current_ai_key_index]

async def check_channel_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return chat_member.status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER 
        ]
    except Exception as e:
        return False

def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def convert_markdown_to_html(markdown_text: str) -> str:
    html_text = escape_html(markdown_text)
    html_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html_text)
    html_text = re.sub(r'__(.*?)__', r'<b>\1</b>', html_text)
    html_text = re.sub(r'(?<!\*)\*(.*?)\*(?!\*)', r'<i>\1</i>', html_text)
    html_text = re.sub(r'(?<!_)_(.*?)_(?!_)', r'<i>\1</i>', html_text)
    html_text = re.sub(r'##\s*(.*?)\n', r'<b>\1</b>\n', html_text)
    html_text = re.sub(r'###\s*(.*?)\n', r'<b>\1</b>\n', html_text)
    html_text = re.sub(r'^\*\s*(.*)', r'&#8226; \1', html_text, flags=re.MULTILINE)
    html_text = re.sub(r'```(.*?)```', r'<code>\1</code>', html_text, flags=re.DOTALL)
    html_text = re.sub(r'`(.*?)`', r'<code>\1</code>', html_text)
    html_text = html_text.replace('\n\n', '\n\n')
    html_text = html_text.replace('\n', '\n')
    return html_text

def split_message(text: str, chunk_size: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    current_chunk_lines = []
    current_length = 0
    lines = text.split('\n') 
    for line in lines:
        if current_length + len(line) + 1 <= chunk_size:
            current_chunk_lines.append(line)
            current_length += len(line) + 1
        else:
            if current_chunk_lines:
                chunks.append('\n'.join(current_chunk_lines))
            current_chunk_lines = [line]
            current_length = len(line) + 1
            while current_length > chunk_size:
                split_point = line.rfind(' ', 0, chunk_size)
                if split_point == -1:
                    split_point = chunk_size
                if split_point == 0:
                    split_point = chunk_size
                chunks.append(line[:split_point].strip())
                line = line[split_point:].strip()
                current_length = len(line)
                current_chunk_lines = [line]
    if current_chunk_lines:
        chunks.append('\n'.join(current_chunk_lines))
    return chunks

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"Hi {user.mention_html()}! I'm NFZ AI. Ask me anything!",
        reply_markup=custom_keyboard
    )
    user_chat_histories[user.id] = []
    user_message_counts[user.id] = 0
    await get_ai_model(user.id)

async def contact_developer_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    developer_keyboard = [[InlineKeyboardButton("Contact Developer", url=DEVELOPER_CONTACT_LINK)]]
    developer_reply_markup = InlineKeyboardMarkup(developer_keyboard)
    await update.message.reply_text(
        "Click the button below to contact the developer:",
        reply_markup=developer_reply_markup
    )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_chat_histories[user_id] = []
    user_message_counts[user_id] = 0
    if user_id in user_ai_models:
        del user_ai_models[user_id]
    await get_ai_model(user_id)
    await update.message.reply_text(
        "Chat history has been reset, and the bot's persona might have changed! You can start a new conversation.",
        reply_markup=custom_keyboard
    )

async def send_animated_response(update: Update, context: ContextTypes.DEFAULT_TYPE, response_text: str):
    formatted_response = convert_markdown_to_html(response_text)
    paragraphs = formatted_response.split('\n\n')
    
    sent_message = await update.message.reply_text(
        paragraphs[0] if paragraphs else "...",
        parse_mode=ParseMode.HTML
    )
    
    current_message = paragraphs[0]
    for paragraph in paragraphs[1:]:
        await asyncio.sleep(0.5)
        current_message += "\n\n" + paragraph
        try:
            await sent_message.edit_text(
                current_message,
                parse_mode=ParseMode.HTML
            )
        except Exception:
            break

    remaining_text = formatted_response[len(current_message):].strip()
    if remaining_text:
        chunks = split_message(remaining_text)
        for chunk in chunks:
            await asyncio.sleep(0.3)
            await update.message.reply_text(
                chunk,
                parse_mode=ParseMode.HTML,
                reply_markup=custom_keyboard
            )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_message = update.message.text
    user_id = user.id

    if user_message == "Start a new conversation":
        await reset_command(update, context)
        return
    elif user_message == "Contact with the Developer":
        await contact_developer_command(update, context)
        return
    
    if user_id not in user_chat_histories:
        user_chat_histories[user_id] = []
    if user_id not in user_message_counts:
        user_message_counts[user_id] = 0 

    user_message_counts[user_id] += 1

    is_member = await check_channel_membership(user_id, context)
    if not is_member:
        channel_keyboard = [[InlineKeyboardButton("Join Channel", url=CHANNEL_LINK)]]
        channel_reply_markup = InlineKeyboardMarkup(channel_keyboard)
        await update.message.reply_text(
            "To continue chatting with me, please join our Telegram channel and text me again!",
            reply_markup=channel_reply_markup
        )
        return

    model = await get_ai_model(user_id)
    await update.message.chat.send_action(ChatAction.TYPING)
    
    user_chat_histories[user.id].append({"role": "user", "parts": [user_message]})

    ai_response = "Sorry, I couldn't get a response from the Server. Please try again later."
    retries = 0
    max_retries = len(GEMINI_API_KEYS) * 2

    while retries < max_retries:
        try:
            chat = model.start_chat(history=user_chat_histories[user.id][:-1]) 
            response = await chat.send_message_async(user_message)
            ai_response = response.text
            break
        except Exception as e:
            retries += 1
            if retries < max_retries:
                new_api_key = await get_next_ai_key()
                genai.configure(api_key=new_api_key)
                del user_ai_models[user.id] 
                model = await get_ai_model(user.id)
                await asyncio.sleep(1)
            else:
                break

    user_chat_histories[user.id].append({"role": "model", "parts": [ai_response]})
    await send_animated_response(update, context, ai_response)

def main() -> None:
    logger.info("NFZ AI Activated")  # This will be the only visible message in green bold
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command)) 
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(MessageHandler(filters.Regex("^Contact with the Developer$"), contact_developer_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
