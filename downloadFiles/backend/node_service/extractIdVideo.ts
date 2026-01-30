
// aqui ele so extrai a id do video. (ex: UrLH86BXQ0E)
export function extractVideoID(url: string): string {
const regex =
  /^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|shorts\/)|youtu\.be\/)([\w-]{11})/;


    const match = url.match(regex);
    if (!match) {
        throw new Error("URL do YouTube é inválida");
    }

    return match[1];
}