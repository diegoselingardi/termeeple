const legacyGame = document.getElementById("legacyGame");
const DAY_INDEX = parseInt(legacyGame.dataset.dayIndex);
const MAX_HISTORICO_EXIBIDO = 5;

let gameOver = false;

function historyKey(day) {
    return `termeeple:legacy:history:${day}`;
}

function loadHistory() {
    try {
        const raw = localStorage.getItem(historyKey(DAY_INDEX));
        return raw ? JSON.parse(raw) : [];
    } catch (e) {
        return [];
    }
}

function saveHistory(history) {
    try {
        localStorage.setItem(historyKey(DAY_INDEX), JSON.stringify(history));
    } catch (e) {
        /* ignora se não der pra salvar */
    }
}

function renderHistory(history) {
    const container = document.getElementById("legacyHistory");
    container.innerHTML = "";
    // mais recente primeiro -- a mensagem de tamanho de cada tentativa não se
    // repete aqui, só aparece uma vez em #legacySizeMessage (a mais atual).
    // Sempre desenha MAX_HISTORICO_EXIBIDO linhas, preenchidas ou vazias -- assim
    // a altura do bloco nunca muda, e o teclado logo abaixo não fica "descendo"
    // conforme os palpites vão sendo enviados.
    const maisRecentesPrimeiro = [...history].reverse().slice(0, MAX_HISTORICO_EXIBIDO);

    for (let i = 0; i < MAX_HISTORICO_EXIBIDO; i++) {
        const tentativa = maisRecentesPrimeiro[i];
        const row = document.createElement("div");
        row.className = "legacy-history__row";

        if (tentativa) {
            const tiles = document.createElement("div");
            tiles.className = "legacy-history__tiles";
            tentativa.evaluation.forEach((item) => {
                const tile = document.createElement("div");
                tile.className = `tile ${item.status}`;
                tile.textContent = item.letter;
                tiles.appendChild(tile);
            });
            row.appendChild(tiles);
        }

        container.appendChild(row);
    }
}

function updateCoins(value) {
    document.getElementById("coinsValue").textContent = value;
}

function showRevealBox(word) {
    document.getElementById("revealBox").textContent = word || "?";
}

function showEndBanner(isWin, palavra) {
    const banner = document.getElementById("revealBanner");
    banner.textContent = isWin
        ? `Parabéns! A palavra era: ${palavra}`
        : "Palavra foi perdida, você nunca saberá qual era.";
    banner.classList.remove("hidden");
}

function disableForm() {
    document.getElementById("legacyInput").disabled = true;
    document.querySelector("#legacyForm button").disabled = true;
}

function updateLudopediaLink(link) {
    const elemento = document.getElementById("ludopediaLink");
    if (link) {
        elemento.innerHTML = `Sobre esse jogo: <a href="${link}" target="_blank" rel="noopener">ver na Ludopedia</a>`;
        elemento.classList.remove("hidden");
    } else {
        elemento.innerHTML = "";
        elemento.classList.add("hidden");
    }
}

fetch("/api/legacy/state")
    .then((response) => response.json())
    .then((data) => {
        updateCoins(data.coins);
        renderHistory(loadHistory());

        if (data.is_game_over) {
            gameOver = true;
            disableForm();
            if (data.is_win) {
                showRevealBox(data.revealed_word);
                updateLudopediaLink(data.ludopedia_link);
            }
            showEndBanner(data.is_win, data.revealed_word);
        }
    });

document.getElementById("legacyForm").addEventListener("submit", (event) => {
    event.preventDefault();
    if (gameOver) return;

    const input = document.getElementById("legacyInput");
    const palpite = input.value.trim();
    if (!palpite) return;

    fetch("/api/legacy/guess", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ guess: palpite, day_index: DAY_INDEX }),
    })
        .then((response) => {
            if (!response.ok) {
                throw new Error("Não foi possível enviar o palpite. Recarregue a página.");
            }
            return response.json();
        })
        .then((data) => {
            updateCoins(data.coins);
            input.value = "";

            if (data.is_win) {
                gameOver = true;
                showRevealBox(data.revealed_word);
                updateLudopediaLink(data.ludopedia_link);
                disableForm();
                recordResult(true);
                showEndBanner(true, data.revealed_word);

                // mostra o palpite vencedor também no histórico, tudo verde
                const historicoVitoria = loadHistory();
                historicoVitoria.push({ sizeMessage: data.size_message, evaluation: data.evaluation });
                saveHistory(historicoVitoria);
                renderHistory(historicoVitoria);

                showStatsPanel();
                return;
            }

            document.getElementById("legacySizeMessage").textContent = data.size_message;

            const history = loadHistory();
            history.push({ sizeMessage: data.size_message, evaluation: data.evaluation });
            saveHistory(history);
            renderHistory(history);

            if (data.is_game_over) {
                gameOver = true;
                disableForm();
                recordResult(false);
                showEndBanner(false);
                showStatsPanel();
            }
        });
});

// -- teclado na tela: escreve no mesmo input do palpite, junto do teclado físico --

function typeLetterLegacy(letra) {
    if (gameOver) return;
    const input = document.getElementById("legacyInput");
    if (input.value.length < 10) {
        input.value += letra.toUpperCase();
    }
}

function doBackspaceLegacy() {
    if (gameOver) return;
    const input = document.getElementById("legacyInput");
    input.value = input.value.slice(0, -1);
}

document.querySelectorAll(".key").forEach((botao) => {
    botao.addEventListener("click", () => {
        const letra = botao.dataset.key;
        if (letra === "BACK") {
            doBackspaceLegacy();
        } else if (letra === "ENTER") {
            document.getElementById("legacyForm").requestSubmit();
        } else {
            typeLetterLegacy(letra);
        }
    });
});

document.getElementById("helpBtn").addEventListener("click", () => {
    document.getElementById("helpPanel").classList.remove("hidden");
    document.getElementById("backdrop").classList.remove("hidden");
});

document.getElementById("closeHelp").addEventListener("click", () => {
    document.getElementById("helpPanel").classList.add("hidden");
    document.getElementById("backdrop").classList.add("hidden");
});

document.getElementById("settingsBtn").addEventListener("click", () => {
    document.getElementById("settingsPanel").classList.remove("hidden");
    document.getElementById("backdrop").classList.remove("hidden");
});

document.getElementById("closeSettings").addEventListener("click", () => {
    document.getElementById("settingsPanel").classList.add("hidden");
    document.getElementById("backdrop").classList.add("hidden");
});

document.getElementById("statsBtn").addEventListener("click", showStatsPanel);

document.getElementById("closeStats").addEventListener("click", () => {
    document.getElementById("statsPanel").classList.add("hidden");
    document.getElementById("backdrop").classList.add("hidden");
});

document.getElementById("backdrop").addEventListener("click", () => {
    document.getElementById("helpPanel").classList.add("hidden");
    document.getElementById("settingsPanel").classList.add("hidden");
    document.getElementById("statsPanel").classList.add("hidden");
    document.getElementById("backdrop").classList.add("hidden");
});

document.getElementById("colorblindToggle").addEventListener("change", (event) => {
    document.body.classList.toggle("colorblind", event.target.checked);
});

// -- estatísticas locais (versão reduzida da de stats.js: sem distribuição de
// tentativas, já que aqui não existe número fixo de tentativas por partida) --

function legacyStatsKey() {
    return "termeeple:stats:legacy";
}

function loadLegacyStats() {
    try {
        const raw = localStorage.getItem(legacyStatsKey());
        if (raw) return JSON.parse(raw);
    } catch (e) {
        /* localStorage indisponível: segue com estatísticas vazias */
    }
    return { gamesPlayed: 0, wins: 0, currentStreak: 0, maxStreak: 0, lastPlayedDay: null };
}

function saveLegacyStats(stats) {
    try {
        localStorage.setItem(legacyStatsKey(), JSON.stringify(stats));
    } catch (e) {
        /* ignora se não der pra salvar */
    }
}

function calcularWinRate(stats) {
    return stats.gamesPlayed > 0 ? Math.round((stats.wins / stats.gamesPlayed) * 100) : 0;
}

function recordResult(won) {
    const stats = loadLegacyStats();

    if (stats.lastPlayedDay === DAY_INDEX) {
        return stats;
    }

    stats.gamesPlayed++;
    if (won) {
        stats.wins++;
        stats.currentStreak = stats.lastPlayedDay === DAY_INDEX - 1 ? stats.currentStreak + 1 : 1;
        stats.maxStreak = Math.max(stats.maxStreak, stats.currentStreak);
    } else {
        stats.currentStreak = 0;
    }

    stats.lastPlayedDay = DAY_INDEX;
    saveLegacyStats(stats);
    return stats;
}

function renderStats() {
    const stats = loadLegacyStats();
    document.getElementById("statGames").textContent = stats.gamesPlayed;
    document.getElementById("statWinRate").textContent = calcularWinRate(stats) + "%";
    document.getElementById("statStreak").textContent = stats.currentStreak;
    document.getElementById("statMaxStreak").textContent = stats.maxStreak;
}

function showStatsPanel() {
    renderStats();
    document.getElementById("statsPanel").classList.remove("hidden");
    document.getElementById("backdrop").classList.remove("hidden");
}

function shareOrCopy(dados, textoClipboard) {
    if (navigator.share) {
        navigator.share(dados).catch(() => {});
    } else if (navigator.clipboard) {
        navigator.clipboard.writeText(textoClipboard).catch(() => {});
    }
}

function shareApp() {
    const titulo = legacyGame.dataset.titulo || "Termeeple Legacy";
    const texto = `Vem jogar ${titulo} comigo -- o Wordle de jogos de tabuleiro!`;
    shareOrCopy(
        { title: titulo, text: texto, url: window.location.origin },
        `${texto} ${window.location.origin}`
    );
}

function shareStats() {
    const stats = loadLegacyStats();
    const winRate = calcularWinRate(stats);
    const titulo = legacyGame.dataset.titulo || "Termeeple Legacy";
    const texto =
        `${titulo} -- minhas estatísticas\n` +
        `🎮 ${stats.gamesPlayed} jogos | ✅ ${winRate}% de vitórias\n` +
        `🔥 Sequência atual: ${stats.currentStreak} | 🏆 Melhor sequência: ${stats.maxStreak}`;
    shareOrCopy({ title: `${titulo} -- minhas estatísticas`, text: texto }, texto);
}

document.getElementById("shareAppBtn").addEventListener("click", shareApp);
document.getElementById("shareStatsBtn").addEventListener("click", shareStats);

if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js");
}
