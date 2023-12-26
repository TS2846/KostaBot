from asyncio import AbstractEventLoop
from typing import Union, Tuple, List
from config import YTDL_OPTIONS
from yt_dlp import YoutubeDL
from dataclasses import dataclass
import asyncio
from concurrent.futures import ProcessPoolExecutor

PPE = ProcessPoolExecutor()


@dataclass
class Song:
    source: Union[str, None]
    title: Union[str, None]
    songId: Union[str, None]


async def extract_music(query: str, loop: AbstractEventLoop, yt: YoutubeDL = None) -> Tuple[List[Song], int]:
    if not yt:
        # create a yt_dlp instance if not already created
        with YoutubeDL(YTDL_OPTIONS) as yt:
            return await extract_music(query, loop, yt)

    # gather song/playlist information
    info = await loop.create_task(asyncio.to_thread(yt.extract_info, query, download=False))

    if not info:
        return [], 1

    if 'entries' in info:
        # this is a play list
        entries = info['entries']
        # process all the songs asynchronously through recursive calls
        tasks = [loop.create_task(extract_music(entry['url'], loop, yt)) for entry in entries]
        result = await asyncio.gather(*tasks)
        # filter songs without errors
        songs = [song[0] for song, _ in result if song]
        err_count = len(entries) - len(songs)
        return songs, err_count
    else:
        # this is a single video
        source = info['url']
        title = info['title'] if 'title' in info else None
        songId = info['id']
        return [Song(source, title, songId)], 0
