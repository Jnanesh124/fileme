import asyncio
from info import *
from utils import *
from time import time
from client import User
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from fuzzywuzzy import fuzz
from pyrogram.errors import ChannelInvalid, FloodWait  # Import relevant exceptions

# Auto-delete duration in seconds
AUTO_DELETE_DURATION = 60  # Adjust this value as needed

@Client.on_message(filters.text & filters.group & filters.incoming & ~filters.command(["verify", "connect", "id"]))
async def search(bot, message):
    f_sub = await force_sub(bot, message)
    if not f_sub:
        return

    # Safe access to 'channels' and 'banned_channels' using get to avoid KeyError
    group_data = await get_group(message.chat.id)
    channels = group_data.get("channels", [])  # Default to empty list if 'channels' is missing
    banned_channels = group_data.get("banned_channels", [])  # Default to empty list if 'banned_channels' is missing

    if not channels:
        return
    if message.text.startswith("/"):
        return

    query = message.text
    searching_msg = await message.reply_text(f"🔍 Searching for '{query}'...")
    results = ""
    head = "<blockquote>👀 Here are the results 👀</blockquote>\n\n"

    try:
        for channel in channels:
            if channel in banned_channels:  # Ignore banned channels
                continue

            # Log channel name and ID
            print(f"Searching in channel: {channel}")

            try:
                async for msg in User.search_messages(chat_id=channel, query=query):
                    if not msg.text and not msg.caption:
                        continue

                    name = (msg.text or msg.caption).split("\n")[0]

                    # Use fuzzy matching to improve accuracy
                    if fuzz.partial_ratio(query.lower(), name.lower()) < 1:
                        continue

                    if name in results:
                        continue

                    results += f"<strong>🍿 {name}</strong>\n<strong>👉🏻 <a href='{msg.link}'>DOWNLOAD</a> 👈🏻</strong>\n\n"

            except ChannelInvalid:
                print(f"Skipping invalid channel: {channel}")
                continue  # Skip this channel and continue with others

        # Ensure the "Searching" message is deleted before sending results or fallback
        await searching_msg.delete()

        if not results:
            movies = await search_imdb(query)
            buttons = [[InlineKeyboardButton(movie['title'], callback_data=f"recheck_{movie['id']}")] for movie in movies]
            msg = await message.reply_text(
                text="<blockquote>😔 Only Type Movie Name 😔</blockquote>",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            msg = await message.reply_text(text=head + results, disable_web_page_preview=True)

        # Auto-delete the result message after the specified duration
        await asyncio.sleep(AUTO_DELETE_DURATION)
        await msg.delete()
    except Exception as e:
        print(f"Error in search: {e}")
        await message.reply_text("❌ An error occurred while searching.")
    finally:
        # Delete the "Searching" message if it still exists (fallback safeguard)
        try:
            await searching_msg.delete()
        except:
            pass


@Client.on_callback_query(filters.regex(r"^recheck"))
async def recheck(bot, update):
    clicked = update.from_user.id
    try:
        typed = update.message.reply_to_message.from_user.id
    except:
        return await update.message.delete()

    if clicked != typed:
        return await update.answer("That's not for you! 👀", show_alert=True)

    m = await update.message.edit("Searching..💥")
    id = update.data.split("_")[-1]
    query = await search_imdb(id)
    group_data = await get_group(update.message.chat.id)
    channels = group_data.get("channels", [])
    banned_channels = group_data.get("banned_channels", [])
    
    head = "<b>👇 I Have Searched Movie With Wrong Spelling But Take care next time 👇</b>\n\n"
    results = ""

    try:
        for channel in channels:
            if channel in banned_channels:
                continue

            try:
                async for msg in User.search_messages(chat_id=channel, query=query):
                    if not msg.text and not msg.caption:
                        continue
                    
                    name = (msg.text or msg.caption).split("\n")[0]
                    
                    if fuzz.partial_ratio(query.lower(), name.lower()) < 70:
                        continue
                    
                    if name in results:
                        continue
                    
                    results += f"<strong>🍿 {name}</strong>\n<strong>👉🏻 <a href='{msg.link}'>DOWNLOAD</a> 👈🏻</strong>\n\n"
            except ChannelInvalid:
                print(f"Skipping invalid channel: {channel}")
                continue  # Skip this channel and continue with others

        if not results:
            return await update.message.edit(
                "<blockquote>🥹 Sorry, no terabox link found ❌\n\nRequest Below 👇 Bot To Get Direct FILE📥</blockquote>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Get Direct FILE Here 📥", url="https://t.me/Theater_Print_Movies_Search_bot")]]))
        
        await update.message.edit(text=head + results, disable_web_page_preview=True)

        # Auto-delete the message after the specified duration
        await asyncio.sleep(AUTO_DELETE_DURATION)
        await update.message.delete()
    except Exception as e:
        await update.message.edit(f"❌ Error: {e}")


@Client.on_callback_query(filters.regex(r"^request"))
async def request(bot, update):
    clicked = update.from_user.id
    try:
        typed = update.message.reply_to_message.from_user.id
    except:
        return await update.message.delete()

    if clicked != typed:
        return await update.answer("That's not for you! 👀", show_alert=True)

    admin = (await get_group(update.message.chat.id))["user_id"]
    id = update.data.split("_")[1]
    name = await search_imdb(id)
    url = "https://www.imdb.com/title/tt" + id
    text = f"#RequestFromYourGroup\n\nName: {name}\nIMDb: {url}"

    msg = await bot.send_message(chat_id=admin, text=text, disable_web_page_preview=True)

    # Auto-delete the message after the specified duration
    await asyncio.sleep(AUTO_DELETE_DURATION)
    await msg.delete()

    await update.answer("✅ Request Sent To Admin", show_alert=True)
    await update.message.delete()
