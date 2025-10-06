from aiohttp import web
import asyncio
import webbrowser
import websockets
import json

class Settings:
    def __init__(self, settings = None):
        self.settings = settings

    async def exit(self):
        self.ws_server.close()
        await self.runner.cleanup()

    async def send_settings(self):
        settings_json = json.dumps(self.settings)

        if self.connected_clients:
            await asyncio.gather(
                *[client.send(settings_json) for client in self.connected_clients]
            )

    async def set_settings_refrence(self, settings):
        self.settings = settings

    async def serve_html(self, request):
        return web.FileResponse('settings.html')

    async def handle_connection(self, websocket):
        # Register WebSocket client
        try:
            async for message in websocket:
                # Parse incoming message
                if message == "hello":
                    self.connected_clients.add(websocket)
                    await self.send_settings()
                else:
                    # Recieve settings
                    settings = json.loads(message)

                    for setting in self.settings:
                        self.settings[setting] = settings[setting]

                    await self.send_settings()

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            # Unregister client
            self.connected_clients.remove(websocket)

    async def start(self):
        print("Launching settings panel.")

        self.loop = asyncio.get_event_loop()

        # Set up http server
        app = web.Application()
        app.router.add_get('/', self.serve_html)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, 'localhost', 8081)
        await self.site.start()

        # Set up websocket server
        self.connected_clients = set()
        self.ws_server = await websockets.serve(self.handle_connection, "localhost", 8766)

        # Open the right webpage
        webbrowser.open_new("http://localhost:8081")
