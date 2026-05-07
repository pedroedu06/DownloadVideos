import { useEffect, useState } from 'react';
import axios from 'axios';
import { IoMdClose } from "react-icons/io";

import './CardDownloadprogress.css';

type Props = {
    job_id: string;
    title: string;
    thumbnail: string;
    onClose: (id: string) => void;
}

type DownloadProgressEvent = {
    job_id: string;
    status?: string;
    progress?: number;
    error?: string | null;
}

const TERMINAL_STATUSES = new Set(["done", "failed", "cancelled"]);

const CardDownloadprogress: React.FC<Props> = ({ job_id, title, thumbnail, onClose }) => {
    const [progress, setProgress] = useState<number>(0);
    const [status, setStatus] = useState<string>("queued");

    useEffect(() => {
        const controller = new AbortController();
        let socket: WebSocket | null = null;
        let reconnectTimer: number | null = null;
        let disposed = false;
        let terminal = false;

        const applyEvent = (event: DownloadProgressEvent) => {
            if (typeof event.progress === "number") {
                setProgress(event.progress);
            }

            if (typeof event.status === "string") {
                setStatus(event.status);

                if (TERMINAL_STATUSES.has(event.status)) {
                    terminal = true;
                    if (event.status === "done") {
                        onClose(job_id);
                    }
                }
            }
        };

        const fetchInitialStatus = async () => {
            try {
                const res = await axios.get(`http://localhost:8000/downloadStatus/${job_id}`, {
                    signal: controller.signal
                });
                applyEvent(res.data);
            } catch (error) {
                if (!axios.isCancel(error)) {
                    console.error("Erro ao buscar status inicial do download:", error);
                }
            }
        };

        const connectSocket = () => {
            if (disposed || terminal) {
                return;
            }

            socket = new WebSocket(`ws://localhost:8000/ws/downloads/${job_id}`);

            socket.onmessage = (message) => {
                try {
                    const data = JSON.parse(message.data) as DownloadProgressEvent;
                    applyEvent(data);

                    if (terminal && socket?.readyState === WebSocket.OPEN) {
                        socket.close();
                    }
                } catch (error) {
                    console.error("Erro ao processar evento do WebSocket:", error);
                }
            };

            socket.onerror = () => {
                if (socket && socket.readyState < WebSocket.CLOSING) {
                    socket.close();
                }
            };

            socket.onclose = () => {
                if (!disposed && !terminal) {
                    reconnectTimer = window.setTimeout(connectSocket, 1000);
                }
            };
        };

        fetchInitialStatus();
        connectSocket();

        return () => {
            disposed = true;
            controller.abort();

            if (reconnectTimer !== null) {
                window.clearTimeout(reconnectTimer);
            }

            if (socket && socket.readyState < WebSocket.CLOSING) {
                socket.close();
            }
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
                        } catch (error) {
                            console.error('Erro ao cancelar download:', error);
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
