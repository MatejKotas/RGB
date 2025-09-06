import asyncio

from RGB import RGB
from album import Album

async def main():
    album = Album()
    rgb = RGB(exit_callback=album.exit, sound_start_callback=album.get_album_cover)

    if album.enabled:
        album.start()
    await rgb.run()

if __name__ == "__main__":
    asyncio.run(main())