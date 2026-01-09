import React from 'react';
import './CardVideo.css';
import { BiLike } from 'react-icons/bi';
import { FaEye } from 'react-icons/fa';

type VideoProps = {
  id: string;
  thumbnail: string;
  title: string;
  likes: number;
  views: number;
};

type VideoConfig = {
  Video: VideoProps;
  onClickDownload: (videoId: string) => void;
}

//aqui e o componente pai, dos componentes de recomendados.
const CardVideo: React.FC<VideoConfig> = ({ Video, onClickDownload }) => {
  return (
    <div className="cv-card">
      <img className="cv-thumbnail" src={Video.thumbnail} alt={Video.title} />
      <div className="cv-title" title={Video.title}>{Video.title}</div>
      <div className="cv-metrics">
        <span className="cv-metric"><BiLike className="cv-icon" /> <span className="cv-number">{Video.likes}</span></span>
        <span className="cv-metric"><FaEye className="cv-icon" /> <span className="cv-number">{Video.views}</span></span>
      </div>
      <div className="cv-download-wrapper">
        <button className="cv-download-btn" onClick={() => onClickDownload(Video.id)}>baixar</button>
      </div>
    </div>
  );
};

export default CardVideo;
