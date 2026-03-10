import re
def extractVideoId(url: str):
    regex = re.compile(r"^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|shorts\/)|youtu\.be\/)([\w-]{11})")

    match = regex.search(url)
    if not match:
        raise ValueError("URL do YouTube e invalida")

    return match[1];