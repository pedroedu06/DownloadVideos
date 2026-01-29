import axios from 'axios';
import CardHistorico from './cardHistorico'
import { useEffect, useState } from 'react'
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

    // Aplicar filtros e ordenação
    const getFilteredAndSortedData = () => {
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
                // Mais recente primeiro (decrescente por data)
                result.sort((a, b) => {
                    const dateA = new Date(a.created_at).getTime();
                    const dateB = new Date(b.created_at).getTime();
                    return dateB - dateA;
                });
                break;

            case 'crescente':
                // Crescente por data (mais antigo primeiro)
                result.sort((a, b) => {
                    const dateA = new Date(a.created_at).getTime();
                    const dateB = new Date(b.created_at).getTime();
                    return dateA - dateB;
                });
                break;

            case 'decrescente':
                // Decrescente por data (mais recente primeiro) - mesmo que recent
                result.sort((a, b) => {
                    const dateA = new Date(a.created_at).getTime();
                    const dateB = new Date(b.created_at).getTime();
                    return dateB - dateA;
                });
                break;

            case 'size':
                // Ordenar por tamanho (maior primeiro)
                result.sort((a, b) => {
                    const sizeA = parseInt(a.size) || 0;
                    const sizeB = parseInt(b.size) || 0;
                    return sizeB - sizeA;
                });
                break;

            default:
                // Para 'video' e 'audio', manter ordem recente
                result.sort((a, b) => {
                    const dateA = new Date(a.created_at).getTime();
                    const dateB = new Date(b.created_at).getTime();
                    return dateB - dateA;
                });
        }

        return result;
    };

    const filteredData = getFilteredAndSortedData();

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