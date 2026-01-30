import { useEffect, useState } from 'react';
import './CardDownloadprogress.css'
import { IoMdClose } from "react-icons/io";
import axios from 'axios';

type Props = {
    job_id: string;
    title: string;
    thumbnail: string;
    onClose: (id: string) => void;
}

const CardDownloadprogress: React.FC<Props> = ({ job_id, title, thumbnail, onClose }) => {
    const [progress, setProgress] = useState<number>(0);
    const [status, setStatus] = useState<string>("queued");

    // Efeito único para polling de status e encerramento (Single source of truth)
    useEffect(() => {
        const controller = new AbortController();
        
        const fetchStatus = async () => {
            try {
                const res = await axios.get(`http://localhost:8000/downloadStatus/${job_id}`, {
                    signal: controller.signal
                });
                
                const data = res.data;
                setProgress(data.progress);
                setStatus(data.status);

                if (data.status === "done" || data.status === "failed") {
                    if (data.status === "done") {
                        onClose(job_id);
                    }
                    return true; // Para o polling
                }
            } catch (err) {
                if (!axios.isCancel(err)) {
                    console.error("Erro ao buscar status de download:", err);
                    return true; // Para o polling em caso de erro crítico
                }
            }
            return false;
        };

        const intervalId = setInterval(async () => {
            const shouldStop = await fetchStatus();
            if (shouldStop) {
                clearInterval(intervalId);
            }
        }, 1000);

        // Executa a primeira vez imediatamente
        fetchStatus();

        return () => {
            controller.abort();
            clearInterval(intervalId);
        };
    }, [job_id, onClose]);

    return (
        <div className='cv-card-progress'>
            <div className='cv-card-progress-container'>
                <div className='cv-card-header'>
                    <div className='cv-video-info-container'>
                        <div className='cv-thumbnail-wrapper'>
                            <img className='cv-video-thumbnail' src={thumbnail || undefined} alt={title} />
                        </div>
                        <div className='cv-video-meta'>
                            <h3 className='cv-video-title' title={title}>{title}</h3>
                            <p className='cv-video-status-text'>
                                {status.charAt(0).toUpperCase() + status.slice(1)}
                            </p>
                        </div>
                    </div>
                    <button className='cv-close-item' onClick={async () => {
                        try {
                            await axios.post(`http://localhost:8000/downloadCancel/${job_id}`);
                        } catch (err) {
                            console.error('Erro ao cancelar download:', err);
                        }
                        onClose(job_id);
                    }} aria-label="fechar">
                        <IoMdClose />
                    </button>
                </div>

                <div className='cv-progressbar-container'>
                    <div className='cv-progressbar-bg' role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)} aria-label={`Progresso de download: ${Math.round(progress)}%`}>
                        <div
                            className='cv-progressbar-fill'
                            style={{
                                width: `${progress}%`,
                                background:
                                    status === "failed" ? "#ef4444" :
                                        "#22c55e" 
                            }}
                        />
                    </div>
                    <div className='cv-progress-label'>{Math.round(progress)}%</div>
                </div>
            </div>
        </div>
    )

}

export default CardDownloadprogress;