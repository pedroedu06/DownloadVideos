import axios from 'axios';
import CardHistorico from './cardHistorico'
import { useMemo, useState, useEffect } from 'react'
import { createUserId } from '../../App';
import { timeAgo } from './ultilitary/timeAgo';
import { bytetoHuman } from './ultilitary/bytestoHuman';
import './historicoGrid.css'

type HistoryProps = {
    job_id: string;
    id: string;
    thumb: string;
    title: string;
    path: string;
    size: string;
    type: string;
    created_at: string;
}



type HistoryGridProps = {
    filter?: string;
}

const HistoryGrid: React.FC<HistoryGridProps> = ({ filter = 'recent' }) => {
    const [data, setData] = useState<HistoryProps[]>([])

    const userId = createUserId();

    useEffect(() => {
        const controller = new AbortController();
        
        const fetchData = async () => {
            try {
                const res = await axios.get(`http://localhost:8000/userDownload/${userId}/downloads`, {
                    signal: controller.signal
                });
                setData(res.data);
            } catch (err) {
                if (!axios.isCancel(err)) {
                    console.error("Erro ao retornar downloads:", err);
                }
            }
        };

        fetchData();
        
        return () => controller.abort();
    }, [userId]);

    // Otimização com useMemo para evitar reprocessamento desnecessário
    const filteredData = useMemo(() => {
        let result = [...data];

        // Filtrar por tipo (vídeo ou áudio)
        if (filter === 'video') {
            result = result.filter(item => item.type?.toLowerCase() === 'video');
        } else if (filter === 'audio') {
            result = result.filter(item => item.type?.toLowerCase() === 'audio');
        }

        // Ordenar
        switch (filter) {
            case 'recent':
            case 'decrescente':
                result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
                break;

            case 'crescente':
                result.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
                break;

            case 'size':
                result.sort((a, b) => (parseInt(b.size) || 0) - (parseInt(a.size) || 0));
                break;

            default:
                result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        }

        return result;
    }, [data, filter]);

    return (
        <div className="sectionGrid">
            {filteredData.length > 0 ? (
                filteredData.map(item => (
                    <div key={item.job_id} className='card'>
                        <CardHistorico 
                            id={`https://www.youtube.com/watch?v=${item.id}`} 
                            title={item.title} 
                            thumb={`https://img.youtube.com/vi/${item.id}/hqdefault.jpg`} 
                            created_at={timeAgo(item.created_at)} 
                            path={item.path} 
                            size={bytetoHuman(item.size)} 
                            type={item.type}
                        />
                    </div>
                ))
            ) : (
                <div style={{ 
                    textAlign: 'center', 
                    padding: '40px 20px', 
                    color: 'var(--text-color)',
                    opacity: 0.5,
                    fontSize: '14px'
                }}>
                    Nenhum download encontrado para este filtro
                </div>
            )}
        </div>
    )
}

export default HistoryGrid;