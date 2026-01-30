import { IoChevronBack } from "react-icons/io5";
import { useNavigate } from "react-router-dom";
import './settings.css'
import { open } from '@tauri-apps/plugin-dialog';
import axios from "axios";
import { useState, useMemo } from "react";
import { FaFolderOpen } from "react-icons/fa";
import { notifySuccess, notifyError } from "../../utils/toast";
import { useTheme } from "../../contexts/ThemeContext";



const Settings = () => {
    const { theme, setTheme } = useTheme();
    const nav = useNavigate();
    
    // Inicialização preguiçosa (Lazy initialization) - Melhor prática de acordo com a doc do React
    const [path, setPath] = useState<string | null>(() => {
        const ph = localStorage.getItem("pathDownloader");
        return ph === "undefined" ? null : ph;
    });
    
    const [videoQuality, setvideoQuality] = useState<string | null>(() => {
        const vq = localStorage.getItem("videoQuality");
        return vq === "auto" ? null : vq;
    });

    const [videoFormat, setvideoFormat] = useState<string | null>(() => {
        const vf = localStorage.getItem("videoFormat");
        return vf === "auto" ? null : vf;
    });

    const [audioFormat, setaudioFormat] = useState<string | null>(() => {
        const af = localStorage.getItem("audioFormat");
        return af === "auto" ? null : af;
    });

    const [audioQuality, setaudioQuality] = useState<string | null>(() => {
        const aq = localStorage.getItem("audioQuality");
        return aq === "auto" ? null : aq;
    });

    const handlesavevideoConfigs = async () => {
        localStorage.setItem("videoFormat", videoFormat ?? "auto")
        localStorage.setItem("videoQuality", videoQuality ?? "auto")

        try {
            await axios.post("http://localhost:8000/downloadSettings", {
                default_video_format: videoFormat,
                video_quality: videoQuality
            })
            notifySuccess("Configurações de vídeo salvas!");
        } catch (error) {
            console.error("Não foi possível salvar as configurações de vídeo:", error)
            notifyError("Erro ao salvar configurações de vídeo.");
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
            notifySuccess("Configurações de áudio salvas!");
        } catch (error) {
            console.error("Não foi possível salvar as configurações de áudio:", error)
            notifyError("Erro ao salvar configurações de áudio.");
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
                notifySuccess("Pasta de download alterada!");
            } catch (error) {
                console.error('Não foi possível salvar o caminho:', error)
                notifyError("Erro ao salvar pasta de download.");
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

    const handleDeleteCache = () => {
        try {
            axios.post("http://localhost:8000/deletCache")
                .then(() => {
                    notifySuccess("Cache limpo com sucesso!");
                })
                .catch(err => {
                    console.error('Erro ao limpar cache:', err);
                    notifyError("Falha ao limpar cache.");
                })
        }
        catch (err) {
            console.error(err);
        }
    }

    const handleDeletData = () => {
        localStorage.removeItem("videoFormat")
        localStorage.removeItem("videoQuality")
        localStorage.removeItem("audioFormat")
        localStorage.removeItem("audioQuality")
        localStorage.removeItem("pathDownloader")

        try {
            axios.post("http://localhost:8000/deletuserSettings")
                .then(() => {
                    notifySuccess("Dados limpos com sucesso!");
                })
                .catch(err => {
                    console.error("Erro ao deletar configurações:", err);
                    notifyError("Erro ao limpar dados.");
                })
        } catch (err) {
            console.error("Erro:", err)
        }

        setPath(null)
        setaudioFormat(null)
        setaudioQuality(null)
        setvideoFormat(null)
        setvideoQuality(null)
    }


    const scrollToSection = (sectionId: string) => {
        const element = document.getElementById(sectionId);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth' });
        }
    };

    return (
        <div className="mainContainer">
            <section className="lateralBar">
                <div className="backBtnContainer">
                    <div className="backBtn" onClick={handleNav}>
                        <IoChevronBack />
                        <span>Voltar</span>
                    </div>
                </div>
                <div className="rowBar" onClick={() => scrollToSection('section-tema')}>Tema</div>
                <div className="rowBar" onClick={() => scrollToSection('section-armazenamento')}>Armazenamento</div>
                <div className="rowBar" onClick={() => scrollToSection('section-video')}>Vídeo</div>
                <div className="rowBar" onClick={() => scrollToSection('section-audio')}>Áudio</div>
                <div className="rowBar" onClick={() => scrollToSection('section-manutencao')}>Manutenção</div>
            </section>
            <section className="mainSection">
                <h2 className="titleSettings">Configurações</h2>
                <div id="section-tema" className="changeBackgroundColor">
                    <h4>Trocar Tema</h4>
                    <div className="changeTheme">
                        <div className={`light ${theme === 'light' ? 'active' : ''}`} onClick={() => setTheme('light')}>Claro</div>
                        <div className={`dark ${theme === 'dark' ? 'active' : ''}`} onClick={() => setTheme('dark')}>Escuro</div>
                        <div className={`midnight ${theme === 'midnight' ? 'active' : ''}`} onClick={() => setTheme('midnight')}>Midnight</div>
                    </div>
                </div>
                <div id="section-armazenamento" className="storageConfig">
                    <h3>Armazenamento</h3>
                    <div className="storageCofigContainer">
                        <button onClick={handleSavePath} className="armazenamentoBtn">
                            <span style={{ color: 'var(--text-color)', marginRight: 10 }}><FaFolderOpen /></span>Selecionar Pasta
                        </button>
                        {path && (
                            <p className="dirSelected">
                                Pasta selecionada:
                                <strong className="pathClass"> {displayPath}</strong>
                            </p>
                        )}
                    </div>
                </div>
                <div id="section-video">
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
                <div id="section-audio">
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
                <div id="section-manutencao">
                    <h3>Manutencao</h3>
                    <div className="row">
                        <span className="LabelBtns">Limpar dados salvos:</span>
                        <button className="limparBtn" onClick={handleDeletData}>Limpar data</button>
                    </div>

                    <div className="row">
                        <span className="LabelBtns">Limpar cache:</span>
                        <button className="limparBtn" onClick={handleDeleteCache}>Limpar Cache</button>
                    </div>

                    <div className="row">
                        <span className="LabelBtns">Exibir histórico de downloads:</span>
                        <button className="limparBtn" onClick={handleHistory}>Histórico</button>

                    </div>
                </div>
            </section>
        </div>
    )
}

export default Settings