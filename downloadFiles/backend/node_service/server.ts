import express from 'express';
import cors from 'cors';
import { getVideos } from './configYT'
import { recommendVideos } from './configrecomendedvideos';
import { extractVideoID } from './extractIdVideo';
import { getInfosVideo } from './getVideo';

const app = express();

app.use(cors());
app.use(express.json());

// ============================================================
// Cache em memória para o /feed com TTL de 5 minutos.
// Evita chamadas repetidas à API do YouTube e acelera o carregamento.
// ============================================================
interface CacheEntry<T> {
    data: T;
    timestamp: number;
}

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutos

let feedCache: CacheEntry<any> | null = null;

app.get('/feed', async (__, res) => {
    try {
        // Verifica se o cache ainda é válido
        const now = Date.now();
        if (feedCache && (now - feedCache.timestamp) < CACHE_TTL_MS) {
            return res.json(feedCache.data);
        }

        const videosInfo = await getVideos();
        const recomendedVideos = recommendVideos(videosInfo);

        // Salva no cache
        feedCache = { data: recomendedVideos, timestamp: now };

        res.json(recomendedVideos);
    } catch (error) {
        console.error("error no /feed:", error);
        res.status(500).json({ error: "falha ao obter os videos" });
    }
});

// Cache de info de vídeos individuais (TTL: 30 minutos)
const VIDEO_CACHE_TTL_MS = 30 * 60 * 1000;
const videoInfoCache = new Map<string, CacheEntry<any>>();

// Limpa cache de vídeos antigos periodicamente (a cada 10 minutos)
setInterval(() => {
    const now = Date.now();
    for (const [key, entry] of videoInfoCache.entries()) {
        if ((now - entry.timestamp) > VIDEO_CACHE_TTL_MS) {
            videoInfoCache.delete(key);
        }
    }
}, 10 * 60 * 1000);

app.post('/getInfoVideo', async (req, res) => {
    try {
        const { url } = req.body;

        if (!url) {
            return res.status(400).json({ error: "url nao enviada!" });
        }

        const VideoId = extractVideoID(url);
        if (!VideoId) {
            return res.status(400).json({ error: "URL inválida" });
        }

        // Verifica cache antes de chamar a API
        const now = Date.now();
        const cached = videoInfoCache.get(VideoId);
        if (cached && (now - cached.timestamp) < VIDEO_CACHE_TTL_MS) {
            return res.json(cached.data);
        }

        const prewiewInfo = await getInfosVideo(VideoId);

        // Salva no cache
        videoInfoCache.set(VideoId, { data: prewiewInfo, timestamp: now });

        res.json(prewiewInfo);
    } catch (error: any) {
        if (error.response?.status === 403) {
            console.error("YouTube bloqueou a requisição (provável limite de API ou IP)");
        } else {
            console.error("Erro no /getInfoVideo:", error);
        }

        res.status(500).json({ error: "Falha ao obter as informações do vídeo" });
    }
});

app.listen(3000, () => {
    console.log('servidor rodando na porta 3000');
});