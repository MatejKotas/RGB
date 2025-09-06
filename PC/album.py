from aiohttp import web
import asyncio
from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import webbrowser
import websockets

class Album:
    def __init__(self, redirect_uri="http://localhost:8081/"):
        # Load variables from .env file
        load_dotenv()
        self.enabled = os.getenv("Enable") == "1"

        if not self.enabled:
            print("Album cover display is not enabled.")
            return

        # Access environment variables
        self.SPOTIFY_CLIENT_ID = os.getenv("ID")
        self.SPOTIFY_CLIENT_SECRET = os.getenv("Secret")
        self.SPOTIFY_REDIRECT_URI = redirect_uri

        self.SCOPE = "user-read-playback-state"

        self.track_playing = False
        self.last_time_left = None

    async def exit(self):
        if self.enabled:
            self.ws_server.close()
            await self.runner.cleanup()

    async def playback_start(self):
        if self.enabled:
            await self.get_album_cover()

    async def command_refresh_album_cover(self):
        if self.enabled:
            await self.get_album_cover(print_message=True)

    async def get_album_cover(self, sleep_amount=0, print_message=False):
        await asyncio.sleep(float(sleep_amount) / 1000)

        if print_message:
            print("Refreshing album cover display.")

        # Get current playback
        current_track = self.sp.current_playback()
        
        if (not current_track) or (not current_track["item"]):
            self.track_playing = False
            album_cover_url = ""

        else:
            self.track_playing = True
            time_left = current_track["item"]["duration_ms"] - current_track["progress_ms"]

            if self.last_time_left == time_left:
                self.track_playing = False

            else:
                self.loop.create_task(self.get_album_cover(time_left))

            # Extract album cover URL
            album_cover_url = current_track["item"]["album"]["images"][0]["url"]

        if self.connected_clients:
            await asyncio.gather(
                *[client.send(album_cover_url) for client in self.connected_clients]
            )

    async def serve_html(self, request):
        return web.FileResponse('album.html')

    async def handle_connection(self, websocket):
        # Register WebSocket client
        try:
            async for message in websocket:
                # Parse incoming message
                if message == "hello":
                    self.connected_clients.add(websocket)
                    await self.get_album_cover()

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # Unregister client
            self.connected_clients.remove(websocket)

    async def start(self):
        if not self.enabled:
            raise Exception("Enviroment not configured for album cover display.")
        print("Setting up album cover display.")

        self.loop = asyncio.get_event_loop()

        # Set up Spotify authentication
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=self.SPOTIFY_CLIENT_ID,
            client_secret=self.SPOTIFY_CLIENT_SECRET,
            redirect_uri=self.SPOTIFY_REDIRECT_URI,
            scope=self.SCOPE
        ))

        # Set up http server
        app = web.Application()
        app.router.add_get('/', self.serve_html)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, 'localhost', 8080)
        await self.site.start()

        # Set up websocket server
        self.connected_clients = set()
        self.ws_server = await websockets.serve(self.handle_connection, "localhost", 8765)

        # Open the right webpage
        webbrowser.open_new("http://localhost:8080")
