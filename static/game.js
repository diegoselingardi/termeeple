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
            day_index: dayIndex,
            attempt_number: currentRow + 1
            })
        })
            .then((response) => response.json())
            .then((data) => {
                for (let i = 0; i < WORD_LENGTH; i++) {
                    const tile = getTile(currentRow, i);
                    const status = data.evaluation[i].status;
                    tile.classList.add(status);                        
                }
                gameOver = data.is_game_over;
                currentRow++;
                currentCol = 0;
            }); 
    }
};

window.addEventListener("keydown", (event) => {
    if (gameOver) {
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

if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/sw.js")        
}