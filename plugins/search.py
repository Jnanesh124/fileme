import asyncio
import base64
import re
from info import *
from utils import *
from time import time
from client import User
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ChannelPrivate, PeerIdInvalid, ChannelInvalid

AUTO_DELETE_DURATION = 60  # Auto-delete duration
RESULTS_PER_PAGE = 5  # Maximum results per page

# Encoding & Decoding Functions
def encode_file_id(file_id):
    return base64.urlsafe_b64encode(file_id.encode()).decode()

def decode_file_id(encoded_id):
    return base64.urlsafe_b64decode(encoded_id).decode()

# Function to sanitize text (removes usernames & links)
def sanitize_text(text):
    if not text:
        return "@ROCKERSBACKUP"
    text = re.sub(r"@\w+", "@ROCKERSBACKUP", text)  # Replace @username
    text = re.sub(r"https?://\S+", "@ROCKERSBACKUP", text)  # Replace links
    text = re.sub(r"www\.", "", text)  # Remove 'www.'
    text = re.sub(r"cinevood", "", text, flags=re.IGNORECASE)  # Remove 'cinevood'
    return text.strip()

# Function to clean query (remove unwanted prefixes but keep main title)
def clean_query(query):
    words = query.split()
    clean_words = [word for word in words if not word.startswith(("@", "http", "www", "-"))]
    return " ".join(clean_words) if clean_words else query  # If empty, return original query

# Pagination Storage
search_results = {}

@Client.on_message(filters.text & filters.group & filters.incoming & ~filters.command(["verify", "connect", "id"]))
async def search(bot, message):
    f_sub = await force_sub(bot, message)
    if not f_sub:
        return

    channels = (await get_group(message.chat.id))["channels"]
    if not channels:
        return

    raw_query = message.text.strip()
    query = clean_query(raw_query)
    requested_by = message.from_user.mention  # Get user who requested

    searching_msg = await message.reply_text(f"🔍 **Searching:** `{query}`", disable_web_page_preview=True)

    results = []
    try:
        for channel in channels:
            try:
                async for msg in User.search_messages(chat_id=channel, query=query):
                    await searching_msg.delete()

                    file_name, file_size = None, None
                    if msg.document:
                        file_name = msg.document.file_name
                        file_size = msg.document.file_size
                    elif msg.video:
                        file_name = msg.video.file_name
                        file_size = msg.video.file_size
                    elif msg.audio:
                        file_name = msg.audio.file_name
                        file_size = msg.audio.file_size

                    if not file_name:
                        continue  

                    file_name = sanitize_text(file_name.split(".")[0])  # Clean title
                    file_id = str(msg.id)
                    encoded_id = encode_file_id(file_id)
                    file_link = f"https://t.me/{channel}?start={encoded_id}"

                    # Convert file size to MB
                    size_mb = f"{file_size / (1024 * 1024):.2f} MB" if file_size else "Unknown Size"

                    results.append(f"📂 **{file_name}**\n📏 **Size:** {size_mb}\n🔗 [Download Here]({file_link})\n")

            except (ChannelPrivate, PeerIdInvalid, ChannelInvalid):
                print(f"Skipping invalid channel: {channel}")
                continue
            except Exception as e:
                print(f"Error accessing channel {channel}: {e}")
                continue

        if not results:
            await searching_msg.delete()
            await message.reply_text(
                "😔 **No results found! Try a different search keyword.**",
                disable_web_page_preview=True
            )
        else:
            search_results[message.chat.id] = {"query": query, "results": results, "requested_by": requested_by}
            await send_results_page(bot, message, page=1)

    except Exception as e:
        await searching_msg.delete()
        print(f"Error: {e}")
        await message.reply_text(f"🚨 **Error:** `{e}`", disable_web_page_preview=True)

async def send_results_page(bot, message, page=1):
    chat_id = message.chat.id
    data = search_results.get(chat_id)

    if not data:
        return await message.reply_text("❌ **No search data found! Try searching again.**")

    results = data["results"]
    query = data["query"]
    requested_by = data["requested_by"]
    total_pages = (len(results) // RESULTS_PER_PAGE) + (1 if len(results) % RESULTS_PER_PAGE != 0 else 0)

    if page < 1 or page > total_pages:
        return

    start_index = (page - 1) * RESULTS_PER_PAGE
    end_index = start_index + RESULTS_PER_PAGE
    paginated_results = results[start_index:end_index]

    # Blockquote format for requested info
    header_text = f"🔍 **Requested Movie:**\n> `{query}`\n\n👤 **Requested By:**\n> {requested_by}\n\n"

    # Generate buttons
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"prev_{page - 1}"))
    buttons.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="pages"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"next_{page + 1}"))

    await message.reply_text(
        header_text + "\n".join(paginated_results),
        reply_markup=InlineKeyboardMarkup([buttons]),
        disable_web_page_preview=True
    )

@Client.on_callback_query(filters.regex(r"^(prev|next)_(\d+)$"))
async def navigate_pages(bot, query):
    action, page = query.data.split("_")
    page = int(page)
    await send_results_page(bot, query.message, page)
    await query.answer()
