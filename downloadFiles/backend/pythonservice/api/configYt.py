import httpx
import os
from dataclasses import dataclass

@dataclass
class VideoInfo:
    id: str
    title: str
    thumbnail: str
    views: int
    publishedAt: str
    score: float = 0.0

api_key = os.getenv('YT_DATA_API_KEY')
api_url = os.getenv('BASE_URL')

if not api_key or not api_url:
    raise ValueError("os dados estao invalidos")

async def getvideos() -> list[VideoInfo]:
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{api_url}/videos", params={
                "key": api_key,
                "part": "snippet,statistics",
                "chart": "mostPopular",
                "maxResults": 20,
                "regionCode": "BR"
            })
            data = res.json()
            return [
                VideoInfo(
                    id=item["id"],
                    title=item["snippet"]["title"],
                    thumbnail=item["snippet"]["thumbnails"]["default"]["url"],
                    views=int(item["statistics"]["viewCount"]),
                    publishedAt=item["snippet"]["publishedAt"]
                )
                for item in data["items"]
            ]
    except Exception as error:
        print(f"log error: {error}")
        raise Exception("error ao buscar os videos!")