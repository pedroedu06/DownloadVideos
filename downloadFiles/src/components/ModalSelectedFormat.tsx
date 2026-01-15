import './ModalSelectedFormat.css'
import { IoIosClose } from "react-icons/io";
import { useState } from 'react';

type ModalProps = {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (type: string) => void;
}

//modal de selecao de formato de donwload.
const ModalSelectedFormat: React.FC<ModalProps> = ({isOpen, onClose, onConfirm}) => {
    const [type, setType] = useState('');

    if (!isOpen) return null;

    return (
        <div className='modalContainer'>
            <div className='modalContent'>
                <div className='modalHeader'>
                    <h2>Selecione o Formato:</h2>
                    <button className='closeBtn' onClick={onClose}><IoIosClose /></button>
                </div>
                <div className='formatSelections'>
                    <label className='formatItem' htmlFor="Video">
                        <span>Video</span>
                        <input type="radio" name="format" id="video" checked={type === 'video'} onChange={() => setType('video')} />
                    </label>
                    <label className='formatItem' htmlFor="Audio">
                        <span>Audio</span>
                        <input type="radio" name="format" id="audio" checked={type === 'audio'} onChange={() => setType('audio')} />
                    </label>
                </div>
                <button className='downloadBtn' onClick={() => {onConfirm(type)}}>Baixar</button>
            </div>
        </div>
    )
}

export default ModalSelectedFormat;