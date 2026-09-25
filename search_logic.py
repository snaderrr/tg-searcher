import asyncio
from telethon import TelegramClient, functions
from telethon.tl.types import (
    InputMessagesFilterPhotos,
    InputMessagesFilterVideo,
    Channel, Chat
)


class TelegramSearcher:
    def __init__(self, api_id, api_hash, session_name='search_session'):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.client = None

    async def connect(self):
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        await self.client.start()

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()

    async def get_creation_date(self, entity):
        if isinstance(entity, Channel) and entity.date:
            return entity.date
        try:
            msgs = await self.client.get_messages(entity, limit=1, reverse=True)
            if msgs:
                return msgs[0].date
        except Exception:
            pass
        return None

    async def count_media(self, entity):
        try:
            photos = await self.client.get_messages(
                entity, limit=0, filter=InputMessagesFilterPhotos()
            )
            videos = await self.client.get_messages(
                entity, limit=0, filter=InputMessagesFilterVideo()
            )
            return photos.total, videos.total
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
                res = await self.client(functions.contacts.SearchRequest(
                    q=q, limit=100
                ))
                for peer in res.chats:
                    if isinstance(peer, (Chat, Channel)):
                        found[peer.id] = peer
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


async def main():
    API_ID = int(input("API_ID: "))
    API_HASH = input("API_HASH: ")

    searcher = TelegramSearcher(API_ID, API_HASH)
    await searcher.connect()

    results = await searcher.search_groups(
        queries=[
            'мои фото', 'наши фото', 'мои видео', 'наши видео',
            'семейные фото', 'фото семьи'
        ],
        keywords=['фото', 'видео', 'мои', 'наши', 'семейн'],
        max_year=2023,
        min_photos=5,
        min_videos=0,
        progress=lambda msg: print(msg)
    )

    print("\n" + "=" * 50)
    for r in results:
        print(f"{r['title']}")
        print(f"  создана: {r['created']} | фото: {r['photos']} | видео: {r['videos']}")
        print(f"  ссылка: {r['link']}")
        print("-" * 50)

    await searcher.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
