let currentRow = 0;
let currentCol = 0;
let dayIndex = null;
let guess = "";
let gameOver = false;
let revealedWord = null;

const board = document.getElementById("board");
const WORD_LENGTH = parseInt(board.dataset.wordLength);
const MAX_ATTEMPTS = parseInt(board.dataset.maxAttempts);
const MODO = board.dataset.modo || "padrao";
const API_PREFIX = MODO === "padrao" ? "" : `/${MODO}`;

fetch(`/api${API_PREFIX}/state`)
    .then((response) => response.json())
    .then((data) => {
        dayIndex = data.day_index;
        restoreBoardState();
    });

function getTile(row, col) {
    return document.getElementById(`tile-${row}-${col}`);
}

function typeLetter(letter) {
    if (gameOver) {
        return;
    }
    if (currentCol < WORD_LENGTH) {
        const tile = getTile(currentRow, currentCol);
        tile.textContent = letter.toUpperCase();
        currentCol++;
    }
}

function doBackspace() {
    if (gameOver) {
        return;
    }       
    if (currentCol > 0) {
        currentCol--;       
        const tile = getTile(currentRow, currentCol);
        tile.textContent = "";
    }
}

function submitGuess() {
    if (gameOver) {
        return;
    }
    if (currentCol === WORD_LENGTH) {
        guess = "";
        for (let i = 0; i < WORD_LENGTH; i++) {
            guess += getTile(currentRow, i).textContent;
        }

        fetch(`/api${API_PREFIX}/guess`, {
            method: "POST",
            headers: {
            "Content-Type": "application/json"
            },
            body: JSON.stringify({
            guess: guess,
            day_index: dayIndex
            })
        })
            .then((response) => {
                if (!response.ok) {
                    throw new Error("Não foi possível enviar o palpite. Recarregue a página.");
                }
                return response.json();
            })
            .then((data) => {
                for (let i = 0; i < WORD_LENGTH; i++) {
                    const tile = getTile(currentRow, i);
                    const status = data.evaluation[i].status;
                    tile.classList.add(status);                        
                }
                gameOver = data.is_game_over;

                if (gameOver) {
                    revealedWord = data.revealed_word;
                    recordResult(data.is_win, currentRow + 1, dayIndex, MODO);
                    updateLudopediaLink(data.ludopedia_link);
                    showRevealBanner(data.is_win, revealedWord);
                    showStatsPanel();
                }

                currentRow++;
                currentCol = 0;
                saveBoardState(); // nova linha
            }); 
    }
};

function isModalOpen() {
    return !document.getElementById("backdrop").classList.contains("hidden");
}

function boardStorageKey(day) {
    return `termeeple:board:${MODO}:${day}`;
}

function saveBoardState() {
    if (dayIndex === null) return;

    const rows = [];
    for (let r = 0; r < MAX_ATTEMPTS; r++) {
        const row = [];
        for (let c = 0; c < WORD_LENGTH; c++) {
            const tile = getTile(r, c);
            const status = tile.classList.contains("correct") ? "correct"
                         : tile.classList.contains("present") ? "present"
                         : tile.classList.contains("absent")  ? "absent"
                         : null;
            row.push({ letter: tile.textContent, status: status });
        }
        rows.push(row);
    }

    const state = { currentRow, currentCol, gameOver, rows, revealedWord };
    try {
        localStorage.setItem(boardStorageKey(dayIndex), JSON.stringify(state));
    } catch (e) {
        /* ignora se não der pra salvar */
    }
}

function restoreBoardState() {
    let saved;
    try {
        const raw = localStorage.getItem(boardStorageKey(dayIndex));
        if (!raw) return;
        saved = JSON.parse(raw);
    } catch (e) {
        return;
    }

    currentRow = saved.currentRow;
    currentCol = saved.currentCol;
    gameOver = saved.gameOver;
    revealedWord = saved.revealedWord || null;

    saved.rows.forEach((row, r) => {
        row.forEach((cell, c) => {
            const tile = getTile(r, c);
            tile.textContent = cell.letter;
            if (cell.status) tile.classList.add(cell.status);
        });
    });

    if (gameOver && revealedWord) {
        const venceu = saved.rows.some((row) => row.every((cell) => cell.status === "correct"));
        showRevealBanner(venceu, revealedWord);
    }
}

function showStatsPanel() {
    renderStats(MODO);
    document.getElementById("statsPanel").classList.remove("hidden");
    document.getElementById("backdrop").classList.remove("hidden");
}

function showRevealBanner(isWin, palavra) {
    const banner = document.getElementById("revealBanner");
    if (!palavra) {
        banner.classList.add("hidden");
        banner.textContent = "";
        return;
    }
    banner.textContent = isWin ? `Parabéns! A palavra era: ${palavra}` : `Palavra certa: ${palavra}`;
    banner.classList.remove("hidden");
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

function typeLetter(letter) {
    if (gameOver) return;
    if (currentCol < WORD_LENGTH) {
        const tile = getTile(currentRow, currentCol);
        tile.textContent = letter.toUpperCase();
        currentCol++;
    }
    saveBoardState(); // nova linha
}

function doBackspace() {
    if (gameOver) return;
    if (currentCol > 0) {
        currentCol--;
        const tile = getTile(currentRow, currentCol);
        tile.textContent = "";
    }
    saveBoardState(); // nova linha
}

window.addEventListener("keydown", (event) => {
    if (gameOver || isModalOpen()) {
        return;
    }

    const ehLetra = /^[a-zA-ZÇç]$/.test(event.key);

    if (ehLetra) {
        typeLetter(event.key);
    }

    if (event.key === "Backspace") {
        doBackspace();
    }

    if (event.key === "Enter") {
        submitGuess();
    }
});

document.querySelectorAll(".key").forEach((botao) => {
    botao.addEventListener("click", () => {
        if (isModalOpen()) {
            return;
        }
        const letra = botao.dataset.key;
        if (letra === "BACK") {
            doBackspace();
        } else if (letra === "ENTER") {
            submitGuess();
        } else {
            typeLetter(letra);
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

function shareApp() {
    const titulo = board.dataset.titulo || "Termeeple";
    const dados = {
        title: titulo,
        text: `Vem jogar ${titulo} comigo -- o Wordle de jogos de tabuleiro!`,
        url: window.location.origin,
    };
    if (navigator.share) {
        navigator.share(dados).catch(() => {});
    } else if (navigator.clipboard) {
        navigator.clipboard.writeText(`${dados.text} ${dados.url}`).catch(() => {});
    }
}

document.getElementById("shareAppBtn").addEventListener("click", shareApp);

document.getElementById("shareStatsBtn").addEventListener("click", () => shareStats(MODO));

if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/sw.js")        
}