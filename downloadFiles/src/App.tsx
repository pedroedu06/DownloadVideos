import "./App.css";
import { getCurrentWindow } from '@tauri-apps/api/window';
import { Route, Routes } from "react-router-dom";
import Home from "./pages/home/home";
import Settings from "./pages/settings/settings";
import History from "./pages/historico/history";
import { ThemeProvider } from "./contexts/ThemeContext";
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

let cachedUserId: string | null = null

export function createUserId() {
  if (cachedUserId) return cachedUserId;

  let id = localStorage.getItem('user_id');

  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("user_id", id);
  }

  cachedUserId = id;
  return id;
}

function App() {

  const close = () => {
    getCurrentWindow().close();
  };
  const minimize = () => {
    getCurrentWindow().minimize();
  };

  return (
    <ThemeProvider>
      <ToastContainer />
      {/* Aqui é a barra de fechar e minimizar o app, isso é global! */}
      <div className="mainContainer">
        <section className="titlebar">
          <button className="close-bar" onClick={close}>X</button>
          <button className="minimize-bar" onClick={minimize}>-</button>
        </section>


        {/* Aqui estão as rotas do app, usando o react-router */}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </div>
    </ThemeProvider>
  );
}

export default App;