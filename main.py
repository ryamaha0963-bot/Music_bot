import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from config import Config
from player import MusicPlayer
from utils import control_buttons

app = Client("music_bot", api_id=Config.API_ID, api_hash=Config.API_HASH, bot_token=Config.BOT_TOKEN)
player = MusicPlayer(app)

@app.on_message(filters.command(["start", "help"]))
async def start_cmd(_, m: Message):
    await m.reply_text(
        "🎧 **Sexy Music Bot**\n\n"
        "🔹 `/play <song name/URL>` – Queue\n"
        "🔹 `/skip` – Next\n"
        "🔹 `/pause` / `/resume` – Toggle\n"
        "🔹 `/stop` – Clear & leave\n"
        "🔹 `/loop` – Toggle repeat\n"
        "🔹 `/queue` – Show queue\n\n"
        "_Made with 🔥 for Railway_"
    )

@app.on_message(filters.command("play"))
async def play_cmd(_, m: Message):
    if len(m.command) < 2:
        return await m.reply("❌ Give a song name or URL.")
    query = " ".join(m.command[1:])
    status, msg = await player.play_song(m.chat.id, query, m.from_user.id)
    await m.reply_text(msg)

@app.on_message(filters.command(["pause", "resume"]))
async def pause_resume_cmd(_, m: Message):
    if m.command[0] == "pause":
        ok = await player.pause(m.chat.id)
        await m.reply("⏸️ Paused." if ok else "❌ Nothing playing.")
    else:
        ok = await player.resume(m.chat.id)
        await m.reply("▶️ Resumed." if ok else "❌ Nothing playing.")

@app.on_message(filters.command("skip"))
async def skip_cmd(_, m: Message):
    ok = await player.skip(m.chat.id)
    await m.reply("⏭️ Skipped." if ok else "❌ Nothing playing.")

@app.on_message(filters.command("stop"))
async def stop_cmd(_, m: Message):
    await player.stop(m.chat.id)
    await m.reply("⏹️ Stopped and cleared queue.")

@app.on_message(filters.command("loop"))
async def loop_cmd(_, m: Message):
    val = player.loop.get(m.chat.id, False)
    player.loop[m.chat.id] = not val
    await m.reply(f"🔁 Loop: {'ON' if not val else 'OFF'}")

@app.on_message(filters.command("queue"))
async def queue_cmd(_, m: Message):
    q = player.queues.get(m.chat.id, [])
    if not q:
        return await m.reply("📭 Queue is empty.")
    text = "📋 **Queue:**\n" + "\n".join([f"{i+1}. {s['title']}" for i, s in enumerate(q[:10])])
    await m.reply(text)

@app.on_callback_query()
async def cb_handler(_, cb: CallbackQuery):
    data = cb.data.split("_")
    action, chat_id = data[0], int(data[1])
    if chat_id != cb.message.chat.id:
        return await cb.answer("Wrong chat!", show_alert=True)

    if action == "pause":
        if player.paused.get(chat_id, False):
            await player.resume(chat_id)
        else:
            await player.pause(chat_id)
        song = player.current.get(chat_id, {})
        await cb.message.edit_text(
            f"🎵 **{song.get('title','Unknown')}**\n⏱️ {song.get('duration','00:00')}",
            reply_markup=control_buttons(chat_id, player.paused.get(chat_id, False), player.loop.get(chat_id, False))
        )
        await cb.answer()

    elif action == "skip":
        await player.skip(chat_id)
        await cb.message.delete()
        await cb.answer("Skipped!")

    elif action == "stop":
        await player.stop(chat_id)
        await cb.message.edit_text("⏹️ Stopped.")
        await cb.answer()

    elif action == "loop":
        player.loop[chat_id] = not player.loop.get(chat_id, False)
        await cb.answer(f"Loop: {'ON' if player.loop[chat_id] else 'OFF'}")
        song = player.current.get(chat_id, {})
        await cb.message.edit_text(
            f"🎵 **{song.get('title','Unknown')}**\n⏱️ {song.get('duration','00:00')}",
            reply_markup=control_buttons(chat_id, player.paused.get(chat_id, False), player.loop.get(chat_id, False))
        )

    elif action == "clear":
        player.queues[chat_id] = []
        await cb.answer("Queue cleared!")

if __name__ == "__main__":
    print("🎵 Bot is starting...")
    app.run()
