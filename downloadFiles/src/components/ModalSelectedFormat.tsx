import './ModalSelectedFormat.css'
import { IoIosClose } from "react-icons/io";
import { useState } from 'react';

type ModalProps = {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (format: string) => void;
}


const ModalSelectedFormat: React.FC<ModalProps> = ({isOpen, onClose, onConfirm}) => {
    const [format, setFormat] = useState('mp4');

    if (!isOpen) return null;

    return (
        <div className='modalContainer'>
            <div className='modalContent'>
                <div className='modalHeader'>
                    <h2>Selecione o Formato:</h2>
                    <button className='closeBtn' onClick={onClose}><IoIosClose /></button>
                </div>
                <div className='formatSelections'>
                    <label className='formatItem' htmlFor="mp4">
                        <span>MP4</span>
                        <input type="radio" name="format" id="mp4" checked={format === 'mp4'} onChange={() => setFormat('mp4')} />
                    </label>
                    <label className='formatItem' htmlFor="mp3">
                        <span>MP3</span>
                        <input type="radio" name="format" id="mp3" checked={format === 'mp3'} onChange={() => setFormat('mp3')} />
                    </label>
                    <label className='formatItem' htmlFor="webm">
                        <span>WEBM</span>
                        <input type="radio" name="format" id="webm" checked={format === 'webm'} onChange={() => setFormat('webm')} />
                    </label>
                </div>
                <button className='downloadBtn' onClick={() => {onConfirm(format)}}>Baixar</button>
            </div>
        </div>
    )
}

export default ModalSelectedFormat;