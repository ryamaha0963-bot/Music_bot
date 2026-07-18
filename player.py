import asyncio
import yt_dlp
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.types import AudioPiped, AudioQuality
from pyrogram import Client as PyroClient
from utils import time_seconds, control_buttons

# FFmpeg settings for crystal clear audio
FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -af \"volume=100\" -acodec libopus -ar 48000 -ac 2"
}

class MusicPlayer:
    def __init__(self, app: PyroClient):
        self.app = app
        # 🔥 YAHAN FIX: 'PyTgCalls' use karo
        self.pytgcalls = PyTgCalls(app)
        self.queues = {}       # chat_id -> list of song dicts
        self.current = {}      # chat_id -> current song dict
        self.loop = {}         # chat_id -> bool
        self.paused = {}       # chat_id -> bool
        self.pytgcalls.start()

    async def play_song(self, chat_id: int, query: str, user_id: int):
        """Adds a song to queue and starts playing if idle."""
        song = await self._extract_song(query, user_id)
        if not song:
            return False, "❌ No results found."
        
        if chat_id not in self.queues:
            self.queues[chat_id] = []
        self.queues[chat_id].append(song)

        if chat_id not in self.current or not self.current[chat_id]:
            await self._start_stream(chat_id)
            return True, f"▶️ **Now playing:** {song['title']}\n⏱️ {song['duration']}\n👤 Requested by {song['requester']}"
        else:
            pos = len(self.queues[chat_id])
            return True, f"📥 **Queued at #{pos}:** {song['title']}"

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
            # Send pretty now‑playing message
            msg = await self.app.send_message(
                chat_id,
                f"🎵 **{song['title']}**\n⏱️ {song['duration']}",
                reply_markup=control_buttons(chat_id)
            )
            # Auto‑poll for end
            asyncio.create_task(self._monitor_stream(chat_id, msg.id))
        except Exception as e:
            await self.app.send_message(chat_id, f"❌ Streaming error: {e}")
            await self._next(chat_id)

    async def _monitor_stream(self, chat_id: int, msg_id: int):
        song = self.current.get(chat_id)
        if song:
            await asyncio.sleep(song.get("raw_duration", 180) + 2)
            if chat_id in self.pytgcalls.active_calls:
                try:
                    await self.pytgcalls.leave_call(chat_id)
                except:
                    pass
            await self._next(chat_id)

    async def _next(self, chat_id: int):
        self.current[chat_id] = None
        if self.loop.get(chat_id, False):
            # Re-add current song to front of queue
            if self.current.get(chat_id):
                self.queues[chat_id].insert(0, self.current[chat_id])
        if not self.queues.get(chat_id):
            await self.app.send_message(chat_id, "⏹️ Queue empty. Leaving VC...")
            try:
                await self.pytgcalls.leave_call(chat_id)
            except:
                pass
            return
        await self._start_stream(chat_id)

    async def pause(self, chat_id: int):
        if chat_id in self.pytgcalls.active_calls:
            self.paused[chat_id] = True
            await self.pytgcalls.pause_stream(chat_id)
            return True
        return False

    async def resume(self, chat_id: int):
        if chat_id in self.pytgcalls.active_calls:
            self.paused[chat_id] = False
            await self.pytgcalls.resume_stream(chat_id)
            return True
        return False

    async def skip(self, chat_id: int):
        if chat_id in self.pytgcalls.active_calls:
            await self.pytgcalls.leave_call(chat_id)
            await self._next(chat_id)
            return True
        return False

    async def stop(self, chat_id: int):
        self.queues[chat_id] = []
        self.current[chat_id] = None
        self.loop[chat_id] = False
        try:
            await self.pytgcalls.leave_call(chat_id)
        except:
            pass
        return True
