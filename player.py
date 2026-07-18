import asyncio
import yt_dlp
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped, AudioQuality, StreamType
from pyrogram import Client as PyroClient
from utils import time_seconds, control_buttons

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -af \"volume=100\" -acodec libopus -ar 48000 -ac 2"
}

class MusicPlayer:
    def __init__(self, app: PyroClient):
        self.app = app
        self.pytgcalls = PyTgCalls(app)
        self.queues = {}
        self.current = {}
        self.loop = {}
        self.paused = {}
        self.pytgcalls.start()

    async def play_song(self, chat_id: int, query: str, user_id: int):
        song = await self._extract_song(query, user_id)
        if not song:
            return False, "❌ No results."
        if chat_id not in self.queues:
            self.queues[chat_id] = []
        self.queues[chat_id].append(song)
        if not self.current.get(chat_id):
            await self._start_stream(chat_id)
            return True, f"▶️ **Now playing:** {song['title']}\n⏱️ {song['duration']}"
        else:
            pos = len(self.queues[chat_id])
            return True, f"📥 **Queued #{pos}:** {song['title']}"

    async def _extract_song(self, query: str, user_id: int):
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "default_search": "ytsearch5",
            "extract_flat": False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
                if "entries" in info:
                    info = info["entries"][0]
                return {
                    "title": info.get("title", "Unknown"),
                    "duration": time_seconds(info.get("duration", 0)),
                    "url": info.get("url") or info.get("webpage_url"),
                    "raw_duration": info.get("duration", 0),
                    "requester": user_id,
                }
            except Exception:
                return None

    async def _start_stream(self, chat_id: int):
        if not self.queues.get(chat_id):
            self.current[chat_id] = None
            return
        song = self.queues[chat_id].pop(0)
        self.current[chat_id] = song
        self.paused[chat_id] = False

        try:
            await self.pytgcalls.join_group_call(
                chat_id,
                AudioPiped(song["url"], ffmpeg_parameters=FFMPEG_OPTS),
                stream_type=StreamType.LOCAL,
                audio_quality=AudioQuality.HIGH,
            )
            msg = await self.app.send_message(
                chat_id,
                f"🎵 **{song['title']}**\n⏱️ {song['duration']}",
                reply_markup=control_buttons(chat_id)
            )
            asyncio.create_task(self._monitor_stream(chat_id, msg.id))
        except Exception as e:
            await self.app.send_message(chat_id, f"❌ Stream error: {e}")
            await self._next(chat_id)

    async def _monitor_stream(self, chat_id: int, msg_id: int):
        song = self.current.get(chat_id)
        if song:
            await asyncio.sleep(song.get("raw_duration", 180) + 2)
            await self._next(chat_id)

    async def _next(self, chat_id: int):
        self.current[chat_id] = None
        if self.loop.get(chat_id, False):
            # Re-add current song (simplified – we skip for now)
            pass
        if not self.queues.get(chat_id):
            await self.app.send_message(chat_id, "⏹️ Queue empty. Leaving...")
            try:
                await self.pytgcalls.leave_call(chat_id)
            except:
                pass
            return
        await self._start_stream(chat_id)

    async def pause(self, chat_id: int):
        try:
            await self.pytgcalls.pause_stream(chat_id)
            self.paused[chat_id] = True
            return True
        except:
            return False

    async def resume(self, chat_id: int):
        try:
            await self.pytgcalls.resume_stream(chat_id)
            self.paused[chat_id] = False
            return True
        except:
            return False

    async def skip(self, chat_id: int):
        try:
            await self.pytgcalls.leave_call(chat_id)
        except:
            pass
        await self._next(chat_id)
        return True

    async def stop(self, chat_id: int):
        self.queues[chat_id] = []
        self.current[chat_id] = None
        self.loop[chat_id] = False
        try:
            await self.pytgcalls.leave_call(chat_id)
        except:
            pass
        return True
