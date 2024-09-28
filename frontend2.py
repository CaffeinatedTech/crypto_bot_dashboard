import asyncio
import json
from aiohttp import web, WSMsgType

bots = {}


class BotEvent(asyncio.Event):
    def __init__(self):
        super().__init__()
        self.bot = None


bots_changed = BotEvent()


async def handle_bot_connection(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    print("New bot connection established")

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data['bot'] not in bots:
                    bots[data['bot']] = {}
                if data['type'] == 'status':
                    this_bot = {
                        'name': data['bot'],
                        'current_price': data['message']['current_price'],
                        'profit': data['message']['profit'],
                        'pnl': data['message']['pnl'],
                        'next_buy_order': data['message']['next_buy'],
                        'next_sell_order': data['message']['next_sell'],
                        'trades': data['message']['trades'],
                        'investment': data['message']['investment'],
                    }
                    bots[data['bot']] = this_bot
                    bots_changed.bot = this_bot
                    bots_changed.set()
                # print(f"Received update from bot - {data}")
            elif msg.type == WSMsgType.ERROR:
                print(f"Bot connection closed with error: {ws.exception()}")
    finally:
        print("Bot connection closed")
    return ws


async def handle_client_connection(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    print("New client connection established")

    try:
        while True:
            await bots_changed.wait()
            await ws.send_json(bots_changed.bot)
            bots_changed.clear()
    except Exception as e:
        print(f"Client connection closed: {str(e)}")
    finally:
        print("Client connection closed")
    return ws


async def handle_http_request(request):
    return web.FileResponse('index.html')


async def init_app():
    app = web.Application()
    app.router.add_get('/', handle_http_request)
    app.router.add_get('/ws', handle_client_connection)
    app.router.add_get('/bot_ws', handle_bot_connection)
    return app


async def main():
    app = await init_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

    print("Server started on http://0.0.0.0:8080")
    print("Client Websocket on ws://0.0.0.0:8080/ws")
    print("Bot Websocket on ws://0.0.0.0:8080/bot_ws")
    print("Press Ctrl+C to stop")

    # This will keep the server running until interrupted
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

