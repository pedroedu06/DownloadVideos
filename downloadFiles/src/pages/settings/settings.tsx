import { IoChevronBack } from "react-icons/io5";
import { useNavigate } from "react-router-dom";
import './settings.css'


const Settings = () => {
    const nav = useNavigate();

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

                </div>
                <div>
                    <h3>Video</h3>
                <div className="videoFormatsSelect">
                    <div className="selectVideoFormat">
                        <label htmlFor="select">Selecione o formato:</label>
                        <div className="select">
                            <select className="selectFormatStandard" value='MP4'>
                                <option value="MP4">MP4</option>
                                <option value="WEBM">WEBM</option>
                            </select>
                        </div>
                    </div>
                    <div className="selectVideoFormat">
                        <label htmlFor="select">Selecione a qualidade:</label>
                        <div className="select">
                            <select className="selectFormatStandard" value='Automatico'>
                                <option value="Automatico">Automatico</option>
                                <option value="480p">480p</option>
                                <option value="720p">720p</option>
                                <option value="1080p">1080p</option>
                            </select>
                            <button className="saveBtn">Salvar</button>
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
                            <select className="selectFormatStandard" value='MP3'>
                                <option value="MP3">MP3</option>
                                <option value="AAC">AAC</option>
                                <option value="WAV">WAV (qualidade alta)</option>
                            </select>

                            <button className="saveBtn">Salvar</button>
                        </div>
                    </div>
                    <div className="selectVideoFormat">
                        <label htmlFor="select" className="label1">Selecione a qualidade de audio:</label>
                        <div className="select">
                            <select className="selectFormatStandard" value='128 kbps'>
                                <option value="128 kbps">128 kbps</option>
                                <option value="192 kbps">192 kbps</option>
                                <option value="320 kbps">320 kbps</option>
                            </select>

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