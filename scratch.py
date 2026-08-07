import asyncio
import aiohttp
import re

async def get_spotify_title(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            text = await response.text()
            match = re.search(r'<title>(.*?)</title>', text)
            if match:
                title = match.group(1)
                # Remove " - song and lyrics by " and " | Spotify"
                title = title.replace(" - song and lyrics by ", " ")
                title = title.split(" | Spotify")[0]
                return title
    return None

async def main():
    print(await get_spotify_title("https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"))

asyncio.run(main())
