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

        if os.getenv("Enable") != "1":
            print("Album cover display is not enabled")
            return

        # Access environment variables
        self.SPOTIFY_CLIENT_ID = os.getenv("ID")
        self.SPOTIFY_CLIENT_SECRET = os.getenv("Secret")
        self.SPOTIFY_REDIRECT_URI = redirect_uri

        self.SCOPE = "user-read-playback-state"

    def exit(self):
        pass # TODO

    def playback_start(self):
        pass # TODO

    async def get_album_cover(self, sleep_amount=0):
        await asyncio.sleep(float(sleep_amount) / 1000)
        print("Refreshing album cover.")

        # Get current playback
        current_track = self.sp.current_playback()
        
        if (not current_track) or (not current_track["item"]):
            self.track_playing = False
            return None

        self.track_playing = True
        time_left = current_track["item"]["duration_ms"] - current_track["progress_ms"]
        asyncio.gather(self.get_album_cover(time_left))

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
                    print("Connected to album cover display.")
                    await self.get_album_cover()

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # Unregister client
            self.connected_clients.remove(websocket)

    def start(self):
        asyncio.run(self.run())

    async def run(self):
        print("Setting up album cover display.")

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
        self.ws_server = None

        # Start websocket server
        self.ws_server = await websockets.serve(self.handle_connection, "localhost", 8765)

        # Open the right webpage
        webbrowser.open_new("http://localhost:8080")

        # Wait for exit
        await self.ws_server.wait_closed()
        await self.runner.cleanup()
