import asyncio
from info import *
from utils import *
from time import time 
from client import User
from pyrogram import Client, filters 
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton 
import re  # We need to use regular expressions for pattern matching
from fuzzywuzzy import fuzz

# Auto-delete duration in seconds
AUTO_DELETE_DURATION = 60  # Adjust this value as needed

# Helper functions for fuzzy search
def levenshtein_distance(str1, str2):
    """Calculates Levenshtein distance between two strings."""
    return fuzz.ratio(str1, str2)

def token_based_matching(query, name):
    """Token-based fuzzy matching."""
    query_tokens = query.split()
    name_tokens = name.split()
    match_score = 0
    for token in query_tokens:
        for name_token in name_tokens:
            match_score += fuzz.ratio(token.lower(), name_token.lower())
    return match_score / len(query_tokens)  # average similarity of all tokens

def threshold_for_similarity(levenshtein_score, token_score):
    """Threshold check for similarity."""
    final_score = (levenshtein_score + token_score) / 2  # average score
    return final_score >= 75, final_score  # Return if it passes threshold and the final score

def ranking_results(result_details):
    """Rank results based on their final score."""
    return sorted(result_details, key=lambda x: x[1], reverse=True)  # Sort by final score (highest first)

def is_valid_movie_name(text):
    """Check if the message contains only valid text (no links, @, or #)."""
    # Check for links, @ or #
    if re.search(r"(https?://|www\.|@|#)", text):
        return False
    return True

@Client.on_message(filters.text & filters.group & filters.incoming & ~filters.command(["verify", "connect", "id"]))
async def search(bot, message):
    if not is_valid_movie_name(message.text):  # If the message contains a link or @, ignore it
        return
    
    f_sub = await force_sub(bot, message)
    if not f_sub:
        return     
    channels = (await get_group(message.chat.id))["channels"]
    if not channels:
        return     
    if message.text.startswith("/"):
        return    

    query = message.text.strip()
    head = "<blockquote>👀 Here are the results 👀</blockquote>\n\n"
    results = ""
    searching_msg = await message.reply_text(text=f"Searching {query}... 💥", disable_web_page_preview=True)

    try:
        # Handle extra words like "dubbed", "tamil", etc., by stripping them
        query = re.sub(r"\s*(dubbed|tamil|english|sub|full\s*movie)\s*", "", query, flags=re.IGNORECASE)

        # To simulate the process, we will store the results in a list and rank them
        result_details = []

        for channel in channels:
            try:
                async for msg in User.search_messages(chat_id=channel, query=query):
                    name = (msg.text or msg.caption).split("\n")[0]
                    if name not in results:
                        # 1. Calculate Levenshtein Distance
                        levenshtein_score = levenshtein_distance(query.lower(), name.lower())
                        
                        # 2. Calculate Token-based Matching score
                        token_score = token_based_matching(query, name)

                        # 3. Check threshold for similarity and calculate final score
                        passes_threshold, final_score_value = threshold_for_similarity(levenshtein_score, token_score)
                        
                        # 4. Show live statistics: Update message with stats for each technique
                        await searching_msg.edit(
                            f"Searching...\n\n"
                            f"Levenshtein Score: {levenshtein_score}%\n"
                            f"Token Score: {token_score}%\n"
                            f"Threshold Passed: {'Yes' if passes_threshold else 'No'}\n"
                            f"Final Score: {final_score_value}%\n"
                            f"Comparing: {name}"
                        )
                        
                        # Only consider results above the threshold (e.g., 75)
                        if passes_threshold:
                            result_details.append((name, final_score_value, msg.link))

            except Exception as e:
                print(f"Error accessing channel {channel}: {e}")
                continue  # Skip this channel and proceed with the next one

        # Sort results by final score in descending order (highest score first)
        result_details = ranking_results(result_details)

        if result_details:
            # Display ranked results
            for name, score, link in result_details:
                results += f"<strong>🍿 {name}</strong>\n<strong>👉🏻 <a href='{link}'>DOWNLOAD</a> 👈🏻</strong>\nScore: {score}%\n\n"
            
            msg = await message.reply_text(text=f"<blockquote>👀 Here are the results 👀</blockquote>\n\n{results}", disable_web_page_preview=True)
        else:
            # No results found, show IMDb button
            movies = await search_imdb(query)
            buttons = [[InlineKeyboardButton(movie['title'], callback_data=f"recheck_{movie['id']}")] for movie in movies]
            msg = await message.reply_text(
                text="<blockquote>😔 No match found. Check out these IMDb suggestions:</blockquote>", 
                reply_markup=InlineKeyboardMarkup(buttons)
            )

        # Delete the searching message after showing the results
        await searching_msg.delete()

        # Auto-delete the result message after the specified duration
        await asyncio.sleep(AUTO_DELETE_DURATION)
        await msg.delete()

    except Exception as e:
        print(f"Error in search: {e}")  # Log the error for debugging
        await searching_msg.edit("❌ Error occurred during search.")

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
    channels = (await get_group(update.message.chat.id))["channels"]
    head = "<b>👇 I Have Searched Movie With Wrong Spelling But Take care next time 👇</b>\n\n"
    results = ""

    try:
        for channel in channels:
            try:
                async for msg in User.search_messages(chat_id=channel, query=query):
                    name = (msg.text or msg.caption).split("\n")[0]
                    if name in results:
                        continue 
                    results += f"<strong>🍿 {name}</strong>\n<strong>👉🏻 <a href='{msg.link}'>DOWNLOAD</a> 👈🏻</strong>\n\n"
            except Exception as e:
                print(f"Error accessing channel {channel}: {e}")
                continue  # Skip this channel and proceed with the next one

        if not results:          
            await update.message.edit(
                "<blockquote>🥹 Sorry, no terabox link found ❌\n\nRequest Below 👇  Bot To Get Direct FILE📥</blockquote>", 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Get Direct FILE Here 📥", url="https://t.me/Theater_Print_Movies_Search_bot")]]))
        else:
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
