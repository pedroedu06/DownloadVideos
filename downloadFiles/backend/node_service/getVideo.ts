import axios from "axios";

const API_URL = process.env.BASE_URL;
const API_KEY = process.env.YT_DATA_API_KEY;

if (!API_KEY) {
    throw new Error("api nao encontrada");
} 

//aqui ele pega as infos basicas do video, titulo e thum e envia para criar o componente de status de download do front!

export async function getInfosVideo(Videoid: string) {
    const { data } = await axios.get(`${API_URL}/videos`, {
        params: {
            part: "snippet",
            id: Videoid,
            key: API_KEY,
        },
    });

    if (!data.items.length){
        throw new Error("Video nao encontrado")
    }

    const snippet = data.items[0].snippet;

    return {
        Videoid,
        title: snippet.title,
        thunbnail: snippet.thumbnails.high.url,
    };
}