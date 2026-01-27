import React, { useState, useRef, useEffect } from "react"
import HistoryGrid from "../componetsHistory/historicoGrid";
import { IoIosArrowBack } from "react-icons/io";
import { GoFilter } from "react-icons/go";
import "./history.css"
import { useNavigate } from "react-router-dom";




const History: React.FC = () => {
    const nav = useNavigate();
    const [isFilterOpen, setIsFilterOpen] = useState(false);
    const [selectedFilter, setSelectedFilter] = useState("recent");
    const filterRef = useRef<HTMLDivElement>(null);

    const backBtn = () => {
        nav('/settings')
    }

    const toggleFilter = () => {
        setIsFilterOpen(!isFilterOpen);
    }

    const handleFilterChange = (value: string) => {
        setSelectedFilter(value);
        setIsFilterOpen(false);
    }

    // Fechar dropdown ao clicar fora
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (filterRef.current && !filterRef.current.contains(event.target as Node)) {
                setIsFilterOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    return (
        <div className="historyContainer">
            <div className="navbarHistory">
                <div className="left">
                    <div className="backBtnHistory" onClick={backBtn}><span><IoIosArrowBack />Voltar</span></div>
                </div>
                <h3>Historico</h3>
                <div className="right">
                    <div className="filterWrapper" ref={filterRef}>
                        <div className="filterHistory" onClick={toggleFilter}>
                            <span><GoFilter />Filtrar</span>
                        </div>
                        {isFilterOpen && (
                            <div className="filterDropdown">
                                <div 
                                    className={`filterOption ${selectedFilter === 'recent' ? 'active' : ''}`}
                                    onClick={() => handleFilterChange('recent')}
                                >
                                    Recente
                                </div>
                                <div 
                                    className={`filterOption ${selectedFilter === 'crescente' ? 'active' : ''}`}
                                    onClick={() => handleFilterChange('crescente')}
                                >
                                    Crescente
                                </div>
                                <div 
                                    className={`filterOption ${selectedFilter === 'decrescente' ? 'active' : ''}`}
                                    onClick={() => handleFilterChange('decrescente')}
                                >
                                    Decrescente
                                </div>
                                <div className="filterDivider"></div>
                                <div 
                                    className={`filterOption ${selectedFilter === 'video' ? 'active' : ''}`}
                                    onClick={() => handleFilterChange('video')}
                                >
                                    Por Vídeo
                                </div>
                                <div 
                                    className={`filterOption ${selectedFilter === 'audio' ? 'active' : ''}`}
                                    onClick={() => handleFilterChange('audio')}
                                >
                                    Por Áudio
                                </div>
                                <div className="filterDivider"></div>
                                <div 
                                    className={`filterOption ${selectedFilter === 'size' ? 'active' : ''}`}
                                    onClick={() => handleFilterChange('size')}
                                >
                                    Por Tamanho
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
            <section className="cardHistorico">
                <HistoryGrid filter={selectedFilter} />
            </section>
        </div>

    )
}

export default History