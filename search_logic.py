import asyncio
from pyrogram import Client
from pyrogram.raw import functions
from pyrogram.raw.types import InputMessagesFilterPhotos, InputMessagesFilterVideo, Channel, Chat


class TelegramSearcher:
    def __init__(self, api_id, api_hash, session_name='search_session'):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.client = None

    async def connect(self):
        self.client = Client(self.session_name, api_id=self.api_id, api_hash=self.api_hash)
        await self.client.start()

    async def disconnect(self):
        if self.client:
            await self.client.stop()

    async def get_creation_date(self, entity):
        if isinstance(entity, Channel) and entity.date:
            return entity.date
        return None

    async def count_media(self, entity):
        try:
            photos = await self.client.invoke(
                functions.messages.SearchRequest(
                    peer=entity, q='', filter=InputMessagesFilterPhotos(), limit=0
                )
            )
            videos = await self.client.invoke(
                functions.messages.SearchRequest(
                    peer=entity, q='', filter=InputMessagesFilterVideo(), limit=0
                )
            )
            return photos.count, videos.count
        except Exception:
            return 0, 0

    async def search_groups(self, queries, keywords, max_year=None,
                            min_photos=0, min_videos=0, progress=None):
        if not self.client:
            await self.connect()

        found = {}
        for i, q in enumerate(queries):
            if progress:
                progress(f"Поиск: {q} ({i+1}/{len(queries)})")
            try:
                res = await self.client.invoke(
                    functions.contacts.SearchRequest(q=q, limit=100)
                )
                for chat in res.chats:
                    if isinstance(chat, (Chat, Channel)):
                        found[chat.id] = chat
                await asyncio.sleep(1)
            except Exception as e:
                if progress:
                    progress(f"Ошибка '{q}': {e}")

        if progress:
            progress(f"Найдено чатов: {len(found)}. Фильтрация...")

        results = []
        for entity in found.values():
            title = getattr(entity, 'title', '') or ''
            if keywords and not any(k.lower() in title.lower() for k in keywords):
                continue

            date = await self.get_creation_date(entity)
            if max_year and date and date.year >= max_year:
                continue

            photo_count, video_count = await self.count_media(entity)
            if photo_count < min_photos or video_count < min_videos:
                continue

            username = getattr(entity, 'username', None)
            link = f"https://t.me/{username}" if username else f"https://t.me/c/{entity.id}"

            results.append({
                'title': title,
                'link': link,
                'created': date.strftime('%Y-%m-%d') if date else '?',
                'year': date.year if date else None,
                'photos': photo_count,
                'videos': video_count,
            })

        results.sort(key=lambda x: (x['year'] or 9999, -x['photos']))
        if progress:
            progress(f"Готово! Найдено: {len(results)}")
        return results
