from api.configYt import VideoInfo
from datetime import datetime, timezone

def calculatedScore(video: VideoInfo) -> float:
    viewsWeight = 0.6
    likesWeight = 0.4
    recentWeight = 0.1

    viewsScore = video.views * viewsWeight
    likesScore = viewsScore * likesWeight

    dateOld = (datetime.now(timezone.utc).timestamp() * 1000 - datetime.fromisoformat(video.publishedAt.replace("Z", "+00:00")).timestamp() * 1000) / (1000 * 60 * 60 * 24)

    recentScore = 100_000 * recentWeight if dateOld < 7 else 0

    return viewsScore + likesScore + recentScore

def recommendVideos(videos: list[VideoInfo]) -> list[VideoInfo]:
    scored = []
    for video in videos:
        video.score = calculatedScore(video)
        scored.append(video)
    return sorted(scored, key=lambda v: v.score or 0, reverse=True)
