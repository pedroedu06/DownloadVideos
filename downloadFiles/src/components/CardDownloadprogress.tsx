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

    const fetchDownloadStatus = async (job_id: string) => {
        try {
            const res = await axios.get(
                `http://localhost:8000/downloadStatus/${job_id}`
            );

            setStatus(res.data.status);
            setProgress(res.data.progress);

            return res.data;
        } catch (err) {
            console.error("erro ao buscar status de download:", err);
            throw err;
        }
    };

    useEffect(() => {
        const interval = setInterval(async () => {
            try {
                const data = await fetchDownloadStatus(job_id);

                if (data.status === "done" || data.status === "failed") {
                    clearInterval(interval);
                }
            } catch {
                clearInterval(interval);
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [job_id]);


    return (
        <div className='cv-card-progress'>
            <div className='cv-card-progress-container'>
                <div className='cv-close-container'>
                    <button className='cv-close-item' onClick={async () => {
                        try {
                            await axios.post(`http://localhost:8000/downloadCancel/${job_id}`);
                        } catch (err) {
                            console.error('erro ao cancelar download:', err);
                        }
                        onClose(job_id);
                    }} aria-label="fechar">
                        <IoMdClose />
                    </button>
                </div>

                <div className='cv-video-info-container'>
                    <img className='cv-video-thumbnail' src={thumbnail} alt={title} />
                    <div className='cv-video-meta'>
                        <h3 className='cv-video-title' title={title}>{title}</h3>
                        <p className='cv-video-status-progress'>{status}</p>
                    </div>
                </div>

                <div className='cv-progressbar-container'>
                    <div className='cv-progressbar-bg' role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress)} aria-label={`Progresso de download: ${Math.round(progress)}%`}>
                        {/* A largura do elemento de fill é controlada pelo progresso (0-100) */}
                        <div
                            className='cv-progressbar-fill'
                            style={{
                                width: `${progress}%`,
                                background:
                                    status === "failed" ? "#dc2626" :
                                        status === "done" ? "#16a34a" :
                                            "#4f46e5"
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