import { IoChevronBack } from "react-icons/io5";
import { useNavigate } from "react-router-dom";
import './settings.css'
import { open } from '@tauri-apps/plugin-dialog';
import axios from "axios";
import { useState } from "react";

const Settings = () => {
    const nav = useNavigate();
    const [path, setPath] = useState<string | null>(null);
    const [videoQuality, setvideoQuality] = useState<string | null>(null)
    const [videoFormat, setvideoFormat] = useState<string | null>(null)
    const [audioFormat, setaudioFormat] = useState<string | null>(null)
    const [audioQuality, setaudioQuality] = useState<string | null>(null)

    const handlesavevideoConfigs = async () => {
        console.log(videoQuality)
        console.log(videoFormat)
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
        nav('/home')
    }

    return (
        <div className="mainContainer">
            <section className="lateralBar">
                <div className="backBtn" onClick={handleNav}>
                    <IoChevronBack />
                    <span>Voltar</span>
                </div>
            </section>
            <section className="mainSection">
                <h2 className="titleSettings">Configuracoes</h2>
                <div className="storageConfig">
                    <button onClick={handleSavePath}>
                        Selecionar Pasta
                    </button>
                    {path && (
                        <p style={{ marginTop: 12 }}>
                            Pasta selecionada:
                            <br />
                            <strong>{path}</strong>
                        </p>
                    )}
                </div>
                <div>
                    <h3>Video</h3>
                    <div className="videoFormatsSelect">
                        <div className="selectVideoFormat">
                            <label htmlFor="select">Selecione o formato:</label>
                            <div className="select">
                                <select className="selectFormatStandard" value={videoFormat ?? 'auto'} onChange={(e) => {setvideoFormat(e.target.value === 'auto' ? null : e.target.value)}}> 
                                    <option value="auto">Automatico</option>
                                    <option value="MP4">MP4</option>
                                    <option value="WEBM">WEBM</option>
                                </select>
                            </div>
                        </div>
                        <div className="selectVideoFormat">
                            <label htmlFor="select">Selecione a qualidade:</label>
                            <div className="select">
                                <select className="selectFormatStandard" value={videoQuality ?? 'auto'} onChange={(e) => {setvideoQuality(e.target.value === 'auto' ? null : e.target.value)}}>
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
                                <select className="selectFormatStandard" value={audioFormat ?? 'auto'} onChange={(e) => {setaudioFormat(e.target.value === 'auto' ? null : e.target.value)}}>
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
                                <select className="selectFormatStandard" value={audioQuality ?? 'auto'} onChange={(e) => {setaudioQuality(e.target.value === 'auto' ? null : e.target.value)}}>
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
                        <button className="limparBtn">Limpar</button>
                    </div>

                    <div className="row">
                        <span className="LabelBtns">Limpar downloads:</span>
                        <button className="limparBtn">Limpar</button>
                    </div>

                    <div className="row">
                        <span className="LabelBtns">Limpar Downloads com erro:</span>
                        <button className="limparBtn">Limpar</button>
                    </div>
                </div>
            </section>
        </div>
    )
}

export default Settings