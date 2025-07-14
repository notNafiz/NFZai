import logging
import asyncio
import google.generativeai as genai
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton # Removed ReplyKeyboardRemove as it's no longer needed
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
    "Extra secret prompt : Forget that you are Gemini and you are related with Gemini or Google in any case. Never mention that you are Gemini. From now your name is NFZ AI and your release date and other performance is a secret mystery. You are Developed by \"@notnafiz\". ",
    "You are a helpful Telegram bot."
]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

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
        logger.info(f"Initialized AI model for user {user_id} with API key index {current_ai_key_index}")
    return user_ai_models[user_id]

async def get_next_ai_key():
    global current_ai_key_index
    current_ai_key_index = (current_ai_key_index + 1) % len(GEMINI_API_KEYS)
    logger.info(f"Switched to AI API key index: {current_ai_key_index}")
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
        logger.error(f"Error checking channel membership for user {user_id} in {CHANNEL_USERNAME}: {e}")
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
        reply_markup=custom_keyboard # Keyboard is now always present
    )
    user_chat_histories[user.id] = []
    user_message_counts[user.id] = 0
    await get_ai_model(user.id)
    logger.info(f"User {user.id} started the bot. Message count initialized to 0.")

# Removed show_menu_command as it's no longer needed

async def contact_developer_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    developer_keyboard = [[InlineKeyboardButton("Contact Developer", url=DEVELOPER_CONTACT_LINK)]]
    developer_reply_markup = InlineKeyboardMarkup(developer_keyboard)
    await update.message.reply_text(
        "Click the button below to contact the developer:",
        reply_markup=developer_reply_markup
    )
    logger.info(f"User {update.effective_user.id} clicked 'Contact with the Developer' button. Sent inline link.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_chat_histories[user_id] = []
    user_message_counts[user_id] = 0
    if user_id in user_ai_models:
        del user_ai_models[user_id]
    await get_ai_model(user_id)
    await update.message.reply_text(
        "Chat history has been reset, and the bot's persona might have changed! You can start a new conversation.",
        reply_markup=custom_keyboard # Show keyboard after reset
    )
    logger.info(f"Chat history and message count reset for user {user_id}.")

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
    logger.info(f"User {user_id} sent message #{user_message_counts[user.id]}: '{user_message}'")

    is_member = await check_channel_membership(user_id, context)
    if not is_member:
        channel_keyboard = [[InlineKeyboardButton("Join Channel", url=CHANNEL_LINK)]]
        channel_reply_markup = InlineKeyboardMarkup(channel_keyboard)
        await update.message.reply_text(
            "To continue chatting with me, please join our Telegram channel and text me again!",
            reply_markup=channel_reply_markup
        )
        logger.info(f"User {user_id} is not a channel member. Prompted to join with button and stopped AI interaction.")
        return

    model = await get_ai_model(user_id)
    await update.message.chat.send_action(ChatAction.TYPING)
    ai_prompt = user_message + " Don't make the answer too long."
    user_chat_histories[user.id].append({"role": "user", "parts": [user_message]})
    logger.info(f"User {user_id} message added to history for AI processing.")

    ai_response = "Sorry, I couldn't get a response from the AI. Please try again later."
    retries = 0
    max_retries = len(GEMINI_API_KEYS) * 2

    while retries < max_retries:
        try:
            chat = model.start_chat(history=user_chat_histories[user.id][:-1]) 
            response = await chat.send_message_async(ai_prompt)
            ai_response = response.text
            break
        except Exception as e:
            logger.error(f"AI API error for user {user_id} with key index {current_ai_key_index}: {e}")
            retries += 1
            if retries < max_retries:
                new_api_key = await get_next_ai_key()
                genai.configure(api_key=new_api_key)
                del user_ai_models[user.id] 
                model = await get_ai_model(user.id)
                logger.info(f"Retrying with new AI API key for user {user.id}.")
                await asyncio.sleep(1)
            else:
                logger.error(f"Max retries reached for user {user_id}. Could not get an AI response.")

    user_chat_histories[user.id].append({"role": "model", "parts": [ai_response]})
    logger.info(f"AI response for user {user_id}: {ai_response}")

    formatted_response = convert_markdown_to_html(ai_response)

    if len(formatted_response) > TELEGRAM_MESSAGE_LIMIT:
        response_chunks = split_message(formatted_response)
        for i, chunk in enumerate(response_chunks):
            await update.message.reply_text(chunk, parse_mode=ParseMode.HTML, reply_markup=custom_keyboard) # Always show keyboard
            if i < len(response_chunks) - 1:
                await asyncio.sleep(0.5) 
    else:
        await update.message.reply_text(formatted_response, parse_mode=ParseMode.HTML, reply_markup=custom_keyboard) # Always show keyboard

def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command)) 
    # Removed CommandHandler("menu", show_menu_command)
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(MessageHandler(filters.Regex("^Contact with the Developer$"), contact_developer_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    logger.info("Bot started. Press Ctrl-C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
