import httpx
import os

api_key = os.getenv('YT_DATA_API_KEY')
api_url = os.getenv('BASE_URL')

if not api_key or not api_url:
    raise ValueError("api ou url nao encontrada ou invalida!")

async def getInfosVideo(VideoId: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{api_url}/videos", params={
                "part": "snippet",
                "id": VideoId,
                "key": api_key
            })
            data = response.json()
        
        if not data.get('items'):
            raise ValueError("Video nao encontrado!")

        snippet = data["items"][0]["snippet"];

        return {
            "id": VideoId,
            "title": snippet["title"],
            "thumbnail": snippet["thumbnails"]["high"]["url"]
        }
    except Exception as error:
        print(f"log error: {error}")
        raise Exception("error ao buscar os videos!")
    