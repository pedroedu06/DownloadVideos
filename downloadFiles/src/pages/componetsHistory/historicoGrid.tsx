import axios from 'axios';
import CardHistorico from './cardHistorico'
import { useEffect, useState } from 'react'
import { createUserId } from '../../App';
import { timeAgo } from './ultilitary/timeAgo';
import { bytetoHuman } from './ultilitary/bytestoHuman';
import './historicoGrid.css'

type HistoryProps = {
    id: string;
    thumb: string;
    title: string;
    path: string;
    size: string;
    type: string;
    created_at: string;
}



const HistoryGrid: React.FC = () => {
    const [data, setData] = useState<HistoryProps[]>([])

    const userId = createUserId();

    useEffect(() => {
        console.log(userId)  
        try {
            axios.get(`http://localhost:8000/userDownload/${userId}/downloads`)
                .then(res => {
                    setData(res.data);
                })
                .catch(err => {
                    console.error("error ao retornar!", err)
                })
            }
        catch (err) {
            console.error(err);
        }
    }, []);

    return (
        <div className="sectionGrid">
            {data.map(item => (
                <div key={item.id} className='card'>
                    <CardHistorico id={`https://www.youtube.com/watch?v=${item.id}`} title={item.title} thumb={`https://img.youtube.com/vi/${item.id}/hqdefault.jpg`} created_at={timeAgo(item.created_at)} path={item.path} size={bytetoHuman(item.size)} type={item.type}/>
                </div>
            ))}
        </div>
    )
}

export default HistoryGrid;