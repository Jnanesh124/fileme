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
    return text

# Function to clean query (remove unwanted prefixes but keep main title)
def clean_query(query):
    words = query.split()
    clean_words = [word for word in words if not word.startswith(("@", "http", "www", "-"))]
    return " ".join(clean_words) if clean_words else query  # If empty, return original query

@Client.on_message(filters.text & filters.group & filters.incoming & ~filters.command(["verify", "connect", "id"]))
async def search(bot, message):
    f_sub = await force_sub(bot, message)
    if not f_sub:
        return

    channels = (await get_group(message.chat.id))["channels"]
    if not channels:
        return

    raw_query = message.text.strip()
    query = clean_query(raw_query)  # Clean query before searching

    searching_msg = await message.reply_text(f"🔍 **Searching:** `{query}`", disable_web_page_preview=True)

    results = ""
    sent_files = 0

    try:
        for channel in channels:
            try:
                async for msg in User.search_messages(chat_id=channel, query=query):
                    await searching_msg.delete()

                    # Identify file type & get filename
                    file_name = None
                    if msg.document:
                        file_name = msg.document.file_name
                    elif msg.video:
                        file_name = msg.video.file_name
                    elif msg.audio:
                        file_name = msg.audio.file_name

                    # Ensure a valid filename exists
                    if not file_name:
                        continue  

                    # Encode file ID for a unique download link
                    file_id = str(msg.id)
                    encoded_id = encode_file_id(file_id)

                    # Generate a shareable link
                    file_link = f"https://t.me/{channel}?start={encoded_id}"
                    title = file_name.split(".")[0]  # Extract title without extension

                    # Prepare caption with sanitized text
                    caption = f"📂 **{sanitize_text(title)}**\n🔗 [Download Here]({file_link})"

                    # Forward file without sender tags
                    await msg.copy(
                        chat_id=message.chat.id,
                        caption=caption
                    )

                    # Append results message
                    results += f"📂 **{sanitize_text(title)}**\n🔗 [Download Here]({file_link})\n\n"
                    sent_files += 1

            except (ChannelPrivate, PeerIdInvalid, ChannelInvalid):
                print(f"Skipping invalid channel: {channel}")
                continue
            except Exception as e:
                print(f"Error accessing channel {channel}: {e}")
                continue

        # If no files were found
        if sent_files == 0:
            await searching_msg.delete()
            await message.reply_text(
                "😔 **No results found! Try a different search keyword.**",
                disable_web_page_preview=True
            )
        else:
            await message.reply_text(results, disable_web_page_preview=True)

    except Exception as e:
        await searching_msg.delete()
        print(f"Error: {e}")
        await message.reply_text(f"🚨 **Error:** `{e}`", disable_web_page_preview=True)
