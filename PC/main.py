import asyncio

from RGB import RGB
from album import Album
from settings import Settings

async def main():
    album = Album()
    settings = Settings()

    if album.enabled:
        rgb = RGB(exit_callback=album.exit, sound_start_callback=album.playback_start, commands={"refresh":album.command_refresh_album_cover}, setting_changed_callback=settings.send_settings)
        await settings.set_settings_refrence(rgb.settings)

        await album.start()
        await settings.start()
        await rgb.run(additional_message='Input "refresh" to refresh the album cover display')
    
    else:
        rgb = RGB(setting_changed_callback=settings.send_settings)
        await settings.set_settings_refrence(rgb.settings)

        await settings.start()
        await rgb.run()

if __name__ == "__main__":
    asyncio.run(main())