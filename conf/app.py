import asyncio
from app.main import create_app

loop = asyncio.get_event_loop()
app = create_app(loop)
