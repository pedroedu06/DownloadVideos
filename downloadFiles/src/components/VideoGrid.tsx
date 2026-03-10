import React from 'react';
import './VideoGrid.css';
import CardVideo from './CardVideo';
import { useEffect, useState } from 'react';

type VideoProps = {
    id: string;
    thumbnail: string;
    title: string;
    likes: number;
    views: number;
};

type VideoDownloadGrid = {
    onClickDownload: (videoId: string) => void
}


// Aqui ele gera os componentes com base no componente pai.
const VideoGrid: React.FC<VideoDownloadGrid> = ({ onClickDownload }) => {

    const [videos, setVideos] = useState<VideoProps[]>([]);
    // Pega os dados da API do YouTube
    useEffect(() => {
        const controller = new AbortController();

        const fetchFeed = async () => {
            try {
                const response = await fetch('http://localhost:8000/feed', {
                    signal: controller.signal
                });
                const dataVideos = await response.json();
                if (Array.isArray(dataVideos)) {
                    setVideos(dataVideos);
                }
            } catch (error: any) {
                if (error.name !== 'AbortError') {
                    console.error("Erro ao carregar o feed:", error);
                }
            }
        };

        fetchFeed();

        return () => controller.abort();
    }, []);


    return (
        <div className="vv-grid-outer" role="region" aria-label="Video grid">
            <div className="vv-grid-scroll">
                <div className="vv-grid-inner">
                    {videos.map((v) => (
                        <CardVideo key={v.id} Video={v} onClickDownload={onClickDownload} />
                    ))}
                </div>
            </div>
        </div>
    );

};

export default VideoGrid;
