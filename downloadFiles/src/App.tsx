import "./App.css";
import { getCurrentWindow } from '@tauri-apps/api/window';
import { Route, Routes } from "react-router-dom";
import Home from "./pages/home/home";
import Settings from "./pages/settings/settings";


function App() {

  const close = () => {
    getCurrentWindow().close();
  };
  const minizimize = () => {
    getCurrentWindow().minimize();
  };

  return (
    <div className="mainContainer">
      <section className="titlebar">
        <button className="close-bar" onClick={close}>X</button>
        <button className="minimize-bar" onClick={minizimize}>-</button>
      </section>



      <Routes>
        <Route path="/*" element={<Home />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </div>


  );
}

export default App;