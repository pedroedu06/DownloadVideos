import React from "react"
import CardHistorico from "../componetsHistory/cardHistorico"
import { IoIosArrowBack } from "react-icons/io";
import { GoFilter } from "react-icons/go";
import "./history.css"
import { useNavigate } from "react-router-dom";




const History: React.FC = () => {
    const nav = useNavigate();

    const backBtn = () => {
        nav('/settings')
    }

    return (
        <div className="historyContainer">
            <div className="navbarHistory">
                <div className="left">
                    <div className="backBtnHistory" onClick={backBtn}><span><IoIosArrowBack />Voltar</span></div>
                </div>
                <h3>Historico</h3>
                <div className="right">
                    <div className="filterHistory"><span><GoFilter />Filtrar</span></div>
                </div>
            </div>
            <CardHistorico id="12313" title="peido" path="downloads" size="2131mb" type="seila" created_at="hoje"/>
        </div>
    )
}

export default History