export function timeAgo(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();

    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 10) return "agora mesmo";
    if (diffSec < 60) return `há ${diffSec} segundos`;
    if (diffMin < 60) return `há ${diffMin} minutos`;
    if (diffHour < 24) return `há ${diffHour} horas`;
    if (diffDay === 1) return "ontem";
    if (diffDay < 7) return `há ${diffDay} dias`;
    if (diffDay < 30) return `há ${Math.floor(diffDay / 7)} semanas`;
    if (diffDay < 365) return `há ${Math.floor(diffDay / 30)} meses`;

    return `há ${Math.floor(diffDay / 365)} anos`;
}