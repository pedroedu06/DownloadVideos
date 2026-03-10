import "./home.css";
import { IoMdDownload } from "react-icons/io";
import { CiSettings } from "react-icons/ci";
import { MdKeyboardArrowLeft } from "react-icons/md";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { GrUpdate } from "react-icons/gr";
import VideoGrid from '../../components/VideoGrid';
import axios from "axios";
import CardDownloadprogress from "../../components/CardDownloadprogress";
import ModalSelectedFormat from "../../components/ModalSelectedFormat";
import { createUserId } from "../../App";

const Home: React.FC = () => {
  // Recarregar a página
  const reload = () => {
    window.location.reload();
  }


  const [open, setOpen] = useState(false);
  const [link, setLink] = useState('');
  const [previews, setPreviews] = useState<Array<{ id: string, title: string, thumbnail: string }>>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [currentPreview, setCurrentPreview] = useState<{ title: string, thumbnail: string } | null>(null);
  const navigateSettings = useNavigate();


  // Aqui confirma o seu download e envia para o worker
  const handleConfirmDownload = async (type: string) => {
    setModalOpen(false);
    try {
      const response = await axios.post('http://localhost:8000/downloadtask', { url: link, type: type, user_id: createUserId() });
      const jobId = response.data.job_id || response.data.jobId || crypto.randomUUID();

      setPreviews(prev => [{ id: jobId, title: currentPreview?.title || 'unknown', thumbnail: currentPreview?.thumbnail ?? "" }, ...prev]);
      setOpen(true);
      setCurrentPreview(null);

    } catch (error) {
      console.error("Erro ao iniciar o download:", error);
      return null;
    }
  }

  // Aqui ele encontra seu vídeo e abre o modal de escolha de formato de download
  const handlePreviewDownload = async () => {
    if (!link) return;
    try {
      const res = await axios.post('http://localhost:8000/getInfoVideo', { url: link });
      const title = res.data.title || 'unknown';
      const thumbnail = res.data.thumbnail || null;
      setCurrentPreview({ title, thumbnail });
      setModalOpen(true);
    } catch (error) {
      console.error('Erro no preview:', error);
    }
  }

  const handleDownloadofGrid = (videoId: string) => {
    const link = `https://www.youtube.com/watch?v=${videoId}`;
    setLink(link)
    handlePreviewDownload()
  }

  const handleSettingsNav = () => {
    navigateSettings('/settings')
  }

  return (
    <div className="home-layout">
      <section className="searchbar-configbtns">
        <div className="search-bar-container">
          <label htmlFor="search-bar-url">Busca: </label>
          <input type="search" className="search-bar" name="search-bar-url" placeholder="Buscar o video" onChange={(e) => setLink(e.target.value)} />
          <button className="download-btn" onClick={handlePreviewDownload}><IoMdDownload /></button>
        </div>
        <div className="buttons-config">
          <button className="updatepage-btn" onClick={reload}><GrUpdate /></button>
          <button className="settings-btn" onClick={handleSettingsNav}><CiSettings /></button>
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
        <VideoGrid onClickDownload={handleDownloadofGrid} />
      </section>

      {open && <div className="sidebar-backdrop" onClick={() => setOpen(false)} />}

      <div className="side-bar">
        <div
          className="sidebar-container"
          style={{
            transform: open ? "translateX(0)" : "translateX(100%)",
          }}
        >
          <div className="sidebar-header">
            <button
              className="sidebar-toggle-btn"
              onClick={() => setOpen(false)}
            >
              <span className="arrow" style={{ transform: 'rotate(180deg)' }}>
                <MdKeyboardArrowLeft />
              </span>
            </button>
          </div>
          <div className="sidebar-content">
            {previews.map(p => (
              <CardDownloadprogress
                key={p.id}
                job_id={p.id}
                title={p.title}
                thumbnail={p.thumbnail}
                onClose={(id) => setPreviews(prev => prev.filter(x => x.id !== id))}
              />
            ))}
          </div>
        </div>

        {!open && (
          <button
            className="sidebar-toggle-btn"
            style={{
              position: "fixed",
              top: "130px",
              right: "0",
              borderRadius: "12px 0 0 12px",
              borderRight: "none",
              width: "34px" // Slightly narrower to look better stuck to the wall
            }}
            onClick={() => setOpen(true)}
          >
            <span className="arrow">
              <MdKeyboardArrowLeft />
            </span>
          </button>
        )}
      </div>
    </div>
  )
}

export default Home;
