let currentRow = 0;
let currentCol = 0;
let dayIndex = null;
let guess = "";
let gameOver = false;

const board = document.getElementById("board");
const WORD_LENGTH = parseInt(board.dataset.wordLength);
const MAX_ATTEMPTS = parseInt(board.dataset.maxAttempts);

fetch("/api/state")
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

        fetch("/api/guess", {
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
                    recordResult(data.is_win, currentRow + 1, dayIndex);
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
    return `termeeple:board:${day}`;
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

    const state = { currentRow, currentCol, gameOver, rows };
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

    saved.rows.forEach((row, r) => {
        row.forEach((cell, c) => {
            const tile = getTile(r, c);
            tile.textContent = cell.letter;
            if (cell.status) tile.classList.add(cell.status);
        });
    });
}

function showStatsPanel() {
    renderStats();
    document.getElementById("statsPanel").classList.remove("hidden");
    document.getElementById("backdrop").classList.remove("hidden");
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

if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/sw.js")        
}