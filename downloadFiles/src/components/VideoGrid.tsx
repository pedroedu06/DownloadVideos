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

type VideoDonwloadGrid = {
    onClickDonwload: (videoId: string) => void
}


// aqui ele gera os componentes, com base no componente pai.
const VideoGrid: React.FC<VideoDonwloadGrid> = ({onClickDonwload}) => {

const [videos, setVideos] = useState<VideoProps[]>([]);
//pega os dados da api do yt
  useEffect(() => {
    fetch('http://localhost:3000/feed')
      .then(res => res.json())
      .then((dataVideos: VideoProps[]) => {
        if (!Array.isArray(dataVideos)) return;
        setVideos(dataVideos);
      });
  }, []);


  return (
    <div className="vv-grid-outer" role="region" aria-label="Video grid">
        <div className="vv-grid-scroll">
            <div className="vv-grid-inner">
                {videos.map((v) => (
                    <CardVideo key={v.id} Video={v} onClickDownload={onClickDonwload} />
                ))}
            </div>
        </div>
    </div>
  );
  
};

export default VideoGrid;
