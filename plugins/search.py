import asyncio
import base64
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import ChannelPrivate, PeerIdInvalid, ChannelInvalid

AUTO_DELETE_DURATION = 60  # Auto-delete time in seconds

def encode_file_id(file_id):
    """Encode file_id to base64 with padding."""
    return base64.urlsafe_b64encode(file_id.encode()).decode().rstrip("=")

def decode_file_id(encoded_id):
    """Decode base64-encoded file_id by adding necessary padding."""
    encoded_id += "=" * (-len(encoded_id) % 4)  # Fix padding
    return base64.urlsafe_b64decode(encoded_id.encode()).decode()

@Client.on_message(filters.text & filters.group & filters.incoming & ~filters.command(["verify", "connect", "id"]))
async def search(bot, message):
    f_sub = await force_sub(bot, message)
    if not f_sub:
        return
    channels = (await get_group(message.chat.id))["channels"]
    if not channels:
        return
    if message.text.startswith("/"):
        return

    query = ' '.join([word for word in message.text.strip().split() if not word.startswith(('#', '@', 'www', 'http'))])

    searching_msg = await message.reply_text(f"<b>Searching:</b> <i>{query}</i>", disable_web_page_preview=True)

    head = "🎬 <b>Search Results</b> 🎬\n\n"
    results = ""
    seen_titles = set()

    try:
        for channel in channels:
            try:
                async for msg in User.search_messages(chat_id=channel, query=query):
                    await searching_msg.delete()

                    if not msg.document and not msg.video and not msg.audio:
                        continue

                    file_id = msg.document.file_id if msg.document else msg.video.file_id if msg.video else msg.audio.file_id
                    encoded_id = encode_file_id(file_id)

                    name = (msg.text or msg.caption or "Unnamed File").split("\n")[0]
                    if name in seen_titles:
                        continue

                    results += f"📂 <b>{name}</b>\n🔗 <a href='https://t.me/Westoftheworldbot}?start={encoded_id}'>📥 Get File</a>\n\n"
                    seen_titles.add(name)

            except (ChannelPrivate, PeerIdInvalid, ChannelInvalid):
                continue
            except Exception as e:
                print(f"Error accessing channel {channel}: {e}")
                continue

        if not results:
            await searching_msg.delete()
            no_results_msg = await message.reply_text(
                text="😔 <b>No files found!</b>\n\n🔍 Try searching with a different name!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Request File", url="https://t.me/Theater_Print_Movies_Search_bot")]])
            )
            await asyncio.sleep(AUTO_DELETE_DURATION)
            await no_results_msg.delete()
        else:
            msg = await message.reply_text(text=head + results, disable_web_page_preview=True)
            await asyncio.sleep(AUTO_DELETE_DURATION)
            await msg.delete()

    except Exception as e:
        await searching_msg.delete()
        await message.reply_text(f"🚨 <b>Error!</b>\n\n⚠️ {e}")

@Client.on_message(filters.command("start") & filters.private)
async def start(bot, message):
    if len(message.command) > 1:
        try:
            file_id = decode_file_id(message.command[1])
            await bot.send_document(chat_id=message.chat.id, document=file_id, caption="📂 Here is your requested file!")
        except Exception as e:
            await message.reply_text(f"🚨 Error retrieving file: {e}")
    else:
        await message.reply_text(
            "👋 Welcome! Use this bot to search and download files.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Search Movies", switch_inline_query_current_chat="")],
                [InlineKeyboardButton("📥 Request File", url="https://t.me/Theater_Print_Movies_Search_bot")]
            ])
        )
