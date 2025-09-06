import asyncio

from RGB import RGB
from album import Album

async def main():
    album = Album()

    if album.enabled:
        rgb = RGB(exit_callback=album.exit, sound_start_callback=album.playback_start, commands={"refresh":album.command_refresh_album_cover})
    
        await album.start()
        await rgb.run(additional_message='Input "refresh" to refresh the album cover display')
    
    else:
        await rgb.run()

if __name__ == "__main__":
    asyncio.run(main())