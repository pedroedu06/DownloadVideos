import { IoChevronBack } from "react-icons/io5";
import { useNavigate } from "react-router-dom";
import './settings.css'
import { open } from '@tauri-apps/plugin-dialog';
import axios from "axios";
import { useState, useEffect, useMemo } from "react";
import { FaFolderOpen } from "react-icons/fa";
import { ToastContainer, toast } from 'react-toastify';
import { useTheme } from "../../contexts/ThemeContext";



const Settings = () => {
    const { theme, setTheme } = useTheme();
    const nav = useNavigate();
    const [path, setPath] = useState<string | null>(null);
    const [videoQuality, setvideoQuality] = useState<string | null>(null)
    const [videoFormat, setvideoFormat] = useState<string | null>(null)
    const [audioFormat, setaudioFormat] = useState<string | null>(null)
    const [audioQuality, setaudioQuality] = useState<string | null>(null)

    const handlesavevideoConfigs = async () => {
        localStorage.setItem("videoFormat", videoFormat ?? "auto")
        localStorage.setItem("videoQuality", videoQuality ?? "auto")

        try {
            await axios.post("http://localhost:8000/downloadSettings", {
                default_video_format: videoFormat,
                video_quality: videoQuality
            })
        } catch (error) {
            console.error("nao foi possivel salvar os formatos (talvez seja os nomes!)", error)
        }
    }

    const handlesaveaudioConfigs = async () => {
        localStorage.setItem("audioFormat", audioFormat ?? "auto")
        localStorage.setItem("audioQuality", audioQuality ?? "auto")

        try {
            await axios.post("http://localhost:8000/downloadSettings", {
                default_audio_format: audioFormat,
                audio_quality: audioQuality
            })
        } catch (error) {
            console.error("nao foi possivel salvar os formatos (talvez seja os nomes!)", error)
        }
    }


    const handleSavePath = async () => {
        const dir = await open({
            directory: true,
            multiple: false
        })

        if (typeof dir === "string") {
            setPath(dir)
            localStorage.setItem("pathDownloader", dir);
            try {
                await axios.post('http://localhost:8000/downloadPath', {
                    path: dir
                })
            } catch (error) {
                console.error('nao foi possivel salvar', error)
            }
        }
    }

    const handleNav = () => {
        nav('/')
    }
    const handleHistory = () => {
        nav('/history')
    }

    const displayPath = useMemo(() => {
        if (!path) return null

        const parts = path.split("\\")
        return parts.length > 3
            ? `${parts[0]}\\${parts[1]}\\...\\${parts[parts.length - 1]}`
            : parts;
    }, [path])

    useEffect(() => {
        const vf = localStorage.getItem("videoFormat")
        const vq = localStorage.getItem("videoQuality")
        const af = localStorage.getItem("audioFormat")
        const aq = localStorage.getItem("audioQuality")
        const ph = localStorage.getItem("pathDownloader")

        setvideoFormat(vf === "auto" ? null : vf)
        setvideoQuality(vq === "auto" ? null : vq)
        setaudioFormat(af === "auto" ? null : af)
        setaudioQuality(aq === "auto" ? null : aq)
        setPath(ph === "undefined" ? null : ph)
    }, [])

    const handleDeletCache = () => {
        localStorage.removeItem("videoFormat")
        localStorage.removeItem("videoQuality")
        localStorage.removeItem("audioFormat")
        localStorage.removeItem("audioQuality")
        localStorage.removeItem("pathDownloader")

        toast('Cache limpo com sucesso', {
            position: "top-center",
            autoClose: 2000,
            hideProgressBar: false,
            closeOnClick: false,
            pauseOnHover: true,
            draggable: true,
            progress: undefined,
            theme: "dark",
        });

        setPath(null)
        setaudioFormat(null)
        setaudioQuality(null)
        setvideoFormat(null)
        setvideoQuality(null)
    }


    return (
        <div className="mainContainer">
            <ToastContainer />
            <section className="lateralBar">
                <div className="backBtn" onClick={handleNav}>
                    <IoChevronBack />
                    <span>Voltar</span>
                </div>
            </section>
            <section className="mainSection">
                <h2 className="titleSettings">Configuracoes</h2>
                <div className="changeBackgroundColor">
                    <h4>Trocar Thema</h4>
                    <div className="changeTheme">
                        <div className={`light ${theme === 'light' ? 'active' : ''}`} onClick={() => setTheme('light')}>Claro</div>
                        <div className={`dark ${theme === 'dark' ? 'active' : ''}`} onClick={() => setTheme('dark')}>Escuro</div>
                        <div className={`midnight ${theme === 'midnight' ? 'active' : ''}`} onClick={() => setTheme('midnight')}>Midnight</div>
                    </div>
                </div> 
                <div className="storageConfig">
                    <h3>Armazenamento</h3>
                    <div className="storageCofigContainer">
                        <button onClick={handleSavePath} className="armazenamentoBtn">
                            <span style={{ color: '#ffff', marginRight: 10 }}><FaFolderOpen /></span>Selecionar Pasta
                        </button>
                        {path && (
                            <p className="dirSelected">
                                Pasta selecionada:
                                <strong className="pathClass">{displayPath}</strong>
                            </p>
                        )}
                    </div>
                </div>
                <div>
                    <h3>Video</h3>
                    <div className="videoFormatsSelect">
                        <div className="selectVideoFormat">
                            <label htmlFor="select">Selecione o formato:</label>
                            <div className="select">
                                <select className="selectFormatStandard" value={videoFormat ?? 'auto'} onChange={(e) => { setvideoFormat(e.target.value === 'auto' ? null : e.target.value) }}>
                                    <option value="auto">Automatico</option>
                                    <option value="MP4">MP4</option>
                                    <option value="WEBM">WEBM</option>
                                </select>
                            </div>
                        </div>
                        <div className="selectVideoFormat">
                            <label htmlFor="select">Selecione a qualidade:</label>
                            <div className="select">
                                <select className="selectFormatStandard" value={videoQuality ?? 'auto'} onChange={(e) => { setvideoQuality(e.target.value === 'auto' ? null : e.target.value) }}>
                                    <option value="auto">Automatico</option>
                                    <option value="480">480p</option>
                                    <option value="720">720p</option>
                                    <option value="1080">1080p</option>
                                </select>
                                <button className="saveBtn" onClick={handlesavevideoConfigs}>Salvar</button>
                            </div>
                        </div>
                    </div>
                </div>
                <div>
                    <h3>Audio</h3>
                    <div className="videoFormatsSelect">
                        <div className="selectVideoFormat">
                            <label htmlFor="select" className="label1">Selecione o formato de audio:</label>
                            <div className="select">
                                <select className="selectFormatStandard" value={audioFormat ?? 'auto'} onChange={(e) => { setaudioFormat(e.target.value === 'auto' ? null : e.target.value) }}>
                                    <option value="auto">Automatico</option>
                                    <option value="MP3">MP3</option>
                                    <option value="AAC">AAC</option>
                                    <option value="WAV">WAV (qualidade alta)</option>
                                </select>
                            </div>
                        </div>
                        <div className="selectVideoFormat">
                            <label htmlFor="select" className="label1">Selecione a qualidade de audio:</label>
                            <div className="select">
                                <select className="selectFormatStandard" value={audioQuality ?? 'auto'} onChange={(e) => { setaudioQuality(e.target.value === 'auto' ? null : e.target.value) }}>
                                    <option value="auto">Automatico</option>
                                    <option value="128">128 kbps</option>
                                    <option value="192">192 kbps</option>
                                    <option value="320">320 kbps</option>
                                </select>
                                <button className="saveBtn" onClick={handlesaveaudioConfigs}>Salvar</button>
                            </div>
                        </div>
                    </div>
                </div>
                <div>
                    <h3>Manutencao</h3>
                    <div className="row">
                        <span className="LabelBtns">Limpar Cache:</span>
                        <button className="limparBtn" onClick={handleDeletCache}>Limpar cache</button>
                    </div>

                    <div className="row">
                        <span className="LabelBtns">Exibir historico de downloads:</span>
                        <button className="limparBtn" onClick={handleHistory}>Historico</button>

                    </div>
                </div>
            </section>
        </div>
    )
}

export default Settings