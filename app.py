from flask import Flask
import asyncio
from threading import Thread
from pyrogram import Client
from pyrogram.types import Message

app = Flask(__name__)

# Your Pyrogram bot class
class Bot(Client):
    def __init__(self):
        super().__init__(
            "movie_bot",  # This serves as the session name
            bot_token="6765313019:AAHYLXnKN_q5dhznb-4IuLddejkCFleIUg8",  # Directly added bot token
            api_id=29942004,  # Directly added API ID
            api_hash="ad92f01e4a90cddebbea0ad16fa23026"  # Directly added API hash
        )

    async def on_message(self, message: Message):
        # Your bot logic goes here
        if message.text:
            await message.reply("Hello! I am your bot.")

    async def start_bot(self):
        print("Starting bot...")
        await self.start()
        print("Bot is now running!")
        await self.idle()  # Keep the bot running

# Flask route for the web server
@app.route('/')
def hello_world():
    return 'GreyMatters'

# Function to run the Pyrogram bot in a separate thread
def run_bot():
    bot = Bot()
    asyncio.run(bot.start_bot())  # Run the Pyrogram bot asynchronously

# Main entry point
if __name__ == "__main__":
    # Start the Flask web server in a separate thread
    flask_thread = Thread(target=lambda: app.run(debug=True, use_reloader=False))
    flask_thread.start()

    # Run the Pyrogram bot in the main thread (or another thread if needed)
    run_bot()
