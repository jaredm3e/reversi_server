const API_URL = '';
let currentGameId = null;
let playerToken = null;
let playerRole = null; // 1 for Black, 2 for White, null for spectator

const boardEl = document.getElementById('board');
const scoreBlackEl = document.getElementById('score-black');
const scoreWhiteEl = document.getElementById('score-white');
const turnIndicatorEl = document.getElementById('turn-indicator');
const statusMessageEl = document.getElementById('status-message');
const newGameBtn = document.getElementById('new-game-btn');
const joiningModal = document.getElementById('joining-modal');

// Modal Elements
const joinBlackBtn = document.getElementById('join-black-btn');
const joinWhiteBtn = document.getElementById('join-white-btn');
const spectateBtn = document.getElementById('spectate-btn');

let gameState = null;

// Initialization: Extract game ID from URL
function init() {
    const path = window.location.pathname;
    const match = path.match(/\/play\/([^\/]+)/);
    if (match) {
        currentGameId = match[1];
        loadTokenFromStorage();
        refreshGameState();
        setupSSE();
    }
}

function setupSSE() {
    if (window.eventSource) window.eventSource.close();

    window.eventSource = new EventSource(`${API_URL}/game/${currentGameId}/events`);

    window.eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'move') {
            updateUI(data.state);
        } else if (data.type === 'claim') {
            refreshGameState(); // Just fetch latest state to see slots
        }
    };

    window.eventSource.onerror = () => {
        console.warn("SSE disconnected, retrying...");
    };
}

function loadTokenFromStorage() {
    const stored = localStorage.getItem(`reversi_auth_${currentGameId}`);
    if (stored) {
        const auth = JSON.parse(stored);
        playerToken = auth.token;
        playerRole = auth.player;
    }
}

function saveTokenToStorage(token, role) {
    localStorage.setItem(`reversi_auth_${currentGameId}`, JSON.stringify({ token, player: role }));
}

async function refreshGameState() {
    if (!currentGameId) return;
    try {
        const response = await fetch(`${API_URL}/game/${currentGameId}`);
        if (response.status === 404) {
            window.location.href = '/play/';
            return;
        }
        const state = await response.json();
        updateUI(state);
    } catch (err) {
        console.error("Poll error:", err);
    }
}

function updateUI(state) {
    gameState = state;

    // Update scores
    scoreBlackEl.textContent = state.scores.black;
    scoreWhiteEl.textContent = state.scores.white;

    // Update turn
    turnIndicatorEl.className = state.current_turn === 1 ? 'black-turn' : 'white-turn';
    turnIndicatorEl.textContent = state.current_turn === 1 ? "BLACK'S TURN" : "WHITE'S TURN";

    if (state.is_over) {
        const winnerText = state.winner === 1 ? "BLACK WINS!" : (state.winner === 2 ? "WHITE WINS!" : "IT'S A DRAW!");
        statusMessageEl.textContent = `GAME OVER: ${winnerText}`;
        turnIndicatorEl.textContent = winnerText;
    } else {
        const roleName = playerRole === 1 ? "Black" : (playerRole === 2 ? "White" : "Spectator");
        statusMessageEl.textContent = `Playing as ${roleName}`;
    }

    // Modal Slot availability
    if (joiningModal.classList.contains('hidden')) {
        // If not shown but we have no role, maybe show it?
        // Let's only show it on first load or manual click.
    } else {
        joinBlackBtn.disabled = state.slots.black === 'filled';
        joinBlackBtn.textContent = state.slots.black === 'filled' ? 'Black (Taken)' : 'Join as Black';
        joinWhiteBtn.disabled = state.slots.white === 'filled';
        joinWhiteBtn.textContent = state.slots.white === 'filled' ? 'White (Taken)' : 'Join as White';
    }

    // If we haven't joined yet and the modal is hidden, show it
    if (playerRole === null && !state.is_over && joiningModal.classList.contains('hidden')) {
        joiningModal.classList.remove('hidden');
    }

    renderBoard(state);
}

function renderBoard(state) {
    boardEl.innerHTML = '';
    const validMoves = state.valid_moves.map(m => `${m[0]},${m[1]}`);

    for (let y = 0; y < 8; y++) {
        for (let x = 0; x < 8; x++) {
            const cell = document.createElement('div');
            cell.className = 'cell';

            const cellValue = state.board[y][x];
            if (cellValue !== 0) {
                const piece = document.createElement('div');
                piece.className = `piece ${cellValue === 1 ? 'black' : 'white'}`;
                cell.appendChild(piece);
            } else if (playerRole === state.current_turn && validMoves.includes(`${x},${y}`)) {
                cell.classList.add('valid-move');
                cell.onclick = () => makeMove(x, y);
            }

            boardEl.appendChild(cell);
        }
    }
}

async function joinAs(role) {
    if (role === null) {
        playerRole = null;
        playerToken = null;
        joiningModal.classList.add('hidden');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/game/${currentGameId}/claim`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player: role })
        });

        if (!response.ok) {
            const err = await response.json();
            alert(err.detail || "Could not claim side");
            return;
        }

        const data = await response.json();
        playerToken = data.token;
        playerRole = data.player;
        saveTokenToStorage(playerToken, playerRole);
        joiningModal.classList.add('hidden');
        refreshGameState();
    } catch (err) {
        alert("Claim error: " + err.message);
    }
}

async function makeMove(x, y) {
    if (!playerToken) return;

    try {
        const response = await fetch(`${API_URL}/game/${currentGameId}/move`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                x: x,
                y: y,
                player: playerRole,
                token: playerToken
            })
        });

        if (!response.ok) {
            const err = await response.json();
            statusMessageEl.textContent = err.detail;
            return;
        }

        const newState = await response.json();
        updateUI(newState);
    } catch (err) {
        statusMessageEl.textContent = "Move Error: " + err.message;
    }
}

joinBlackBtn.onclick = () => joinAs(1);
joinWhiteBtn.onclick = () => joinAs(2);
spectateBtn.onclick = () => joinAs(null);

newGameBtn.onclick = () => {
    window.location.href = '/play/';
};

init();
