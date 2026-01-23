import React from 'react';
import './cardHistorico.css'
import { FaFolderOpen } from "react-icons/fa";
import { FaFile } from "react-icons/fa";
import { IoIosPlay } from "react-icons/io";
import { MdOutlineDateRange } from "react-icons/md";



type HistoryProps = {
    id: string;
    title: string;
    path: string;
    size: string;
    type: string;
    created_at: string;
}


const CardHistorico: React.FC<HistoryProps> = ({ id, title, path, size, type, created_at }) => {
    return (
        <div className='cardContainer'>
            <img className="ch-thumbnail" src="" />
            <div className='ch-title'><span>{title}</span></div>
            <div className='ch-idyt'>{id}</div>
            <div className='ch-metrics'>
                <span className='ch-path'><span style={{ color: "#fff" }}><FaFolderOpen /></span>{path}</span>
                <span className='ch-path'><span style={{ color: "#fff" }}><FaFile /></span>{size}</span>
                <span className='ch-type'><span style={{ color: "#fff" }}><IoIosPlay /></span>{type}</span>
                <span className='ch-date'><span style={{ color: "#fff" }}><MdOutlineDateRange /></span>{created_at}</span>
            </div>
        </div>
    );
}

export default CardHistorico;
