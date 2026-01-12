import { IoChevronBack } from "react-icons/io5";
import './settings.css'


const Settings = () => {
    return (
        <div className="mainContainer">
            <section className="lateralBar">
                <div className="backBtn">
                    <IoChevronBack />
                    <span>Voltar</span>
                </div>
            </section>
            <section className="mainSection">
                <h2 className="titleSettings">Configuracoes</h2>
                <div className="storageConfig">

                </div>
                <div className="videoFormatsSelect">
                    <div className="selectVideoFormat">
                        <label htmlFor="select">Selecione o formato padrao:</label>
                        <select className="selectFormatStandard" value='MP4'>
                            <option value="MP4">MP4</option>
                            <option value="WEBM">WEBM</option>
                        </select>
                        <button className="saveBtn">Salvar</button>
                    </div>
                    <div className="selectQualit">
                        <label htmlFor="select">Selecione a qualidade padrao:</label>
                        <select className="selectQualit" value='Automatico'>
                            <option value="Automatico">Automatico</option>
                            <option value="480p">480p</option>
                            <option value="720p">720p</option>
                            <option value="1080p">1080p</option>
                        </select>
                        <button className="saveBtn">Salvar</button>
                    </div>
                </div>
                <div className="audioFormatSelect">
                    <div className="selectAudioFormat">
                        <label htmlFor="select">Selecione o formato de audio padrao:</label>
                        <select className="selectFormatStandard" value='MP3'>
                            <option value="MP3">MP3</option>
                            <option value="AAC">AAC</option>
                            <option value="WAV">WAV (qualidade alta)</option>
                        </select>
                        <button className="saveBtn">Salvar</button>
                    </div>
                    <div className="selectQualit">
                        <label htmlFor="select">Selecione a qualidade de audio padrao:</label>
                        <select className="selectQualit" value='128 kbps'>
                            <option value="128 kbps">128 kbps</option>
                            <option value="192 kbps">192 kbps</option>
                            <option value="320 kbps">320 kbps</option>
                        </select>
                        <button className="saveBtn">Salvar</button>
                    </div>
                </div>

            </section>

        </div>
    )
}

export default Settings