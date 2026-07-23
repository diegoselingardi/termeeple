function statsKey(modo) {
    return `termeeple:stats:${modo}`;
}

function getMaxAttempts() {
    const board = document.getElementById("board");
    return parseInt(board.dataset.maxAttempts) || 6;
}

function loadStats(modo) {
    try {
        const raw = localStorage.getItem(statsKey(modo));
        if (raw) return JSON.parse(raw);
    } catch (e) {
        /* localStorage indisponível: segue com estatísticas vazias */
    }
    return {
        gamesPlayed: 0,
        wins: 0,
        currentStreak: 0,
        maxStreak: 0,
        distribution: new Array(getMaxAttempts()).fill(0),
        lastPlayedDay: null,
    };
}

function saveStats(modo, stats) {
    try {
        localStorage.setItem(statsKey(modo), JSON.stringify(stats));
    } catch (e) {
        /* ignora se não der pra salvar */
    }
}

function recordResult(won, attemptsUsed, dayIndex, modo) {
    const stats = loadStats(modo);

    // trava contra contagem duplicada -- se a pessoa recarregar a página
    // depois de já ter terminado o jogo de hoje, isso impede contar de novo
    if (stats.lastPlayedDay === dayIndex) {
        return stats;
    }

    stats.gamesPlayed++;

    if (won) {
        stats.wins++;
        stats.distribution[attemptsUsed - 1]++;
        // sequência só continua se o dia anterior também foi jogado
        stats.currentStreak = (stats.lastPlayedDay === dayIndex - 1) ? stats.currentStreak + 1 : 1;
        stats.maxStreak = Math.max(stats.maxStreak, stats.currentStreak);
    } else {
        stats.currentStreak = 0;
    }

    stats.lastPlayedDay = dayIndex;
    saveStats(modo, stats);
    return stats;
}

function renderStats(modo) {
    const stats = loadStats(modo);
    const winRate = stats.gamesPlayed > 0 ? Math.round((stats.wins / stats.gamesPlayed) * 100) : 0;

    document.getElementById("statGames").textContent = stats.gamesPlayed;
    document.getElementById("statWinRate").textContent = winRate + "%";
    document.getElementById("statStreak").textContent = stats.currentStreak;
    document.getElementById("statMaxStreak").textContent = stats.maxStreak;

    const distList = document.getElementById("distList");
    distList.innerHTML = "";
    const maxCount = Math.max(...stats.distribution, 1);

    stats.distribution.forEach((count, i) => {
        const pct = Math.max((count / maxCount) * 100, 8);
        const row = document.createElement("div");
        row.className = "dist-row";
        row.innerHTML = `
            <span class="dist-row__label">${i + 1}</span>
            <div class="dist-row__bar-wrap">
                <div class="dist-row__bar" style="width:${pct}%">${count}</div>
            </div>
        `;
        distList.appendChild(row);
    });
}

function shareStats(modo) {
    const stats = loadStats(modo);
    const winRate = stats.gamesPlayed > 0 ? Math.round((stats.wins / stats.gamesPlayed) * 100) : 0;
    const titulo = document.getElementById("board").dataset.titulo || "Termeeple";
    const distribuicao = stats.distribution.map((count, i) => `${i + 1}: ${count}`).join("\n");

    const texto =
        `${titulo} -- minhas estatísticas\n` +
        `🎮 ${stats.gamesPlayed} jogos | ✅ ${winRate}% de vitórias\n` +
        `🔥 Sequência atual: ${stats.currentStreak} | 🏆 Melhor sequência: ${stats.maxStreak}\n\n` +
        `Distribuição de tentativas:\n${distribuicao}`;

    if (navigator.share) {
        navigator.share({ title: `${titulo} -- minhas estatísticas`, text: texto }).catch(() => {});
    } else if (navigator.clipboard) {
        navigator.clipboard.writeText(texto).catch(() => {});
    }
}
