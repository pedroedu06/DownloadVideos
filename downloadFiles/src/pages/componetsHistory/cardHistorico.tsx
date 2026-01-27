import React from 'react';
import './cardHistorico.css'
import { FaFolderOpen } from "react-icons/fa";
import { FaFile } from "react-icons/fa";
import { IoIosPlay } from "react-icons/io";
import { MdOutlineDateRange } from "react-icons/md";

type HistoryProps = {
    id: string;
    thumb: string;
    title: string;
    path: string;
    size: string;
    type: string;
    created_at: string;
}


const CardHistorico: React.FC<HistoryProps> = ({ id, thumb, title, path, size, type, created_at }) => {
    return (
        <div className='cardContainer'>
            <div className='ch-thumb-container'>
                <img className="ch-thumbnail" src={thumb} />
            </div>
            <div className='ch-container'>
                <div className='ch-title'>Titulo do video: <span className='contain'>{title}</span></div>
                <div className='ch-idyt'>Id do youtube do video: <span className='contain'>{id}</span></div>

                <div className='ch-metrics-container'>
                    <div className="metric metric-path">
                        <FaFolderOpen />
                        <span className="label">Path:</span>
                        <span className="path-txt">{path}</span>
                    </div>

                    <div className="metric">
                        <FaFile />
                        <span className="label">Tamanho:</span>
                        <span className="value">{size}</span>
                    </div>

                    <div className="metric">
                        <IoIosPlay />
                        <span className="label">Tipo:</span>
                        <span className="value">{type}</span>
                    </div>

                    <div className="metric">
                        <MdOutlineDateRange />
                        <span className="label">Data:</span>
                        <span className="value">{created_at}</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default CardHistorico;
