import "./App.css";
import { getCurrentWindow } from '@tauri-apps/api/window';
import { IoMdDownload } from "react-icons/io";
import { CiSettings } from "react-icons/ci";
import { MdKeyboardArrowLeft } from "react-icons/md";
import { useState } from "react";
import { GrUpdate } from "react-icons/gr";
import VideoGrid from './components/VideoGrid';
import axios from "axios";
import CardDownloadprogress from "./components/CardDownloadprogress";
import ModalSelectedFormat from "./components/ModalSelectedFormat";


function App() {
  const [open, setOpen] = useState(false);
  const [link, setLink] = useState('');
  const [previews, setPreviews] = useState<Array<{id:string,title:string,thumbnail:string}>>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [currentPreview, setCurrentPreview] = useState<{title:string,thumbnail:string} | null>(null);


  const close = () => {
    getCurrentWindow().close();
  };
  const minizimize = () => {
    getCurrentWindow().minimize();
  };

  const handleConfirmDownload = async (format: string) => {
    setModalOpen(false);
    try {
      const response = await axios.post('http://localhost:8000/downloadtask', { url: link, format });
      console.log('Download iniciado:', response.data);
      const jobId = response.data.job_id || response.data.jobId || crypto.randomUUID();

      setPreviews(prev => [{id: jobId, title: currentPreview?.title || 'unknown', thumbnail: currentPreview?.thumbnail || 'unknown'}, ...prev]);
      setOpen(true);
      setCurrentPreview(null);
      
    } catch (error) {
      console.log("erro ao iniciar o donwload", error)
      return null;
    }
  }

  const handlePreviewDownload = async () => {
    if (!link) return;
    try {
      const res = await axios.post('http://localhost:3000/getInfoVideo', { url: link });
      console.log('Preview info:', res.data);
      const title = res.data.title || 'unknown';
      const thumbnail = res.data.thumbnail || null;
      setCurrentPreview({ title, thumbnail });
      setModalOpen(true);
    } catch (error) {
      console.log('error no preview', error);
    }
  }

  return (
    <div className="mainContainer">
      <section className="titlebar">
        <button className="close-bar" onClick={close}>X</button>
        <button className="minimize-bar" onClick={minizimize}>-</button>
      </section>

      <section className="searchbar-configbtns">
        <div className="search-bar-container">
          <label htmlFor="search-bar-url">Busca: </label>
          <input type="search" className="search-bar" name="search-bar-url" placeholder="Buscar o video" onChange={(e) => setLink(e.target.value)} />
          <button className="download-btn" onClick={handlePreviewDownload}><IoMdDownload /></button>
        </div>
        <div className="buttons-config">
          <button className="updatepage-btn"><GrUpdate /></button>
          <button className="settings-btn"><CiSettings /></button>
        </div>
      </section>

      <section className="modalFormatSelect">
        <ModalSelectedFormat
          isOpen={modalOpen}
          onClose={() => { setModalOpen(false); setCurrentPreview(null); }}
          onConfirm={handleConfirmDownload}
        />
        
      </section>

      <section className="YT-Feed">
        <VideoGrid />
      </section>

      {open && <div className="sidebar-backdrop" />}

      <div className="side-bar" style={{ position: "relative" }}>
        <div
          className="sidebar-container"
          style={{
            transform: open ? "translateX(0)" : "translateX(100%)",
            transition: "transform 0.35s cubic-bezier(.4,0,.2,1)",
            position: "relative",
            zIndex: 2,
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            padding: '12px'
          }}
        >
          {previews.map(p => (
            <CardDownloadprogress key={p.id} job_id={p.id} title={p.title} thumbnail={p.thumbnail} onClose={(id)=> setPreviews(prev => prev.filter(x => x.id !== id))} />
          ))}
        </div>
        <button
          className="sidebar-toggle-btn"
          style={{
            position: "absolute",
            top: "16px",
            right: open ? "330px" : "0px",
            zIndex: 3,
            height: "46px",
            width: "40px",
            background: "rgb(56, 58, 75)",
            border: "none",
            borderRadius: "16px 0 0 16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            transition: "right 0.35s cubic-bezier(.4,0,.2,1), background 0.2s, border-radius 0.2s",
          }}
          onClick={() => setOpen((v) => !v)}
        >
          <span
            className="arrow"
            style={{
              fontSize: 35,
              color: "#fff",
              transition: "transform 0.3s cubic-bezier(.4,0,.2,1)",
              transform: open ? "rotate(180deg)" : "rotate(0deg)",
              userSelect: "none",
            }}
          >
            <MdKeyboardArrowLeft />
          </span>
        </button>
      </div>
    </div>
  );
}

export default App;