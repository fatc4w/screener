// Main Application Logic

class PokerTrainer {
    constructor() {
        this.engine = pokerEngine;
        this.ranges = preflopRanges;
        this.solver = gtoSolver;
        
        // Game state
        this.settings = {
            startingSpot: 'flop',
            preflopAction: 'srp',
            gameType: 'cash',
            stakes: 'NL500'
        };
        
        this.session = {
            hands: 0,
            moves: 0,
            score: 0,
            bestMoves: 0,
            correctMoves: 0,
            inaccuracies: 0,
            wrongMoves: 0,
            blunders: 0,
            totalEVLoss: 0,
            history: []
        };
        
        this.currentHand = null;
        this.currentGTOStrategy = null;
        
        this.init();
    }

    init() {
        try {
            this.setupEventListeners();
            this.showScreen('settings');
        } catch (error) {
            console.error('Error in init():', error);
            throw error;
        }
    }

    setupEventListeners() {
        // Settings screen
        const startBtn = document.getElementById('start-training-btn');
        if (startBtn) {
            startBtn.addEventListener('click', () => {
                console.log('Start button clicked');
                this.startTraining();
            });
        } else {
            console.error('Start button not found!');
        }
        
        
        document.querySelectorAll('.btn-option').forEach(btn => {
            btn.addEventListener('click', (e) => {
                console.log('Button clicked:', e.target.dataset);
                const group = e.target.closest('.button-group');
                if (group) {
                    group.querySelectorAll('.btn-option').forEach(b => b.classList.remove('active'));
                }
                e.target.classList.add('active');
                
                if (e.target.dataset.start) {
                    this.settings.startingSpot = e.target.dataset.start;
                }
                if (e.target.dataset.action) {
                    this.settings.preflopAction = e.target.dataset.action;
                }
            });
        });
        
        // Game screen
        document.getElementById('back-to-settings').addEventListener('click', () => {
            this.showScreen('settings');
        });
        
        document.querySelectorAll('.action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                const size = parseFloat(e.currentTarget.dataset.size) || 0;
                this.handlePlayerAction(action, size);
            });
        });
    }

    showScreen(screenName) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.remove('active');
        });
        document.getElementById(`${screenName}-screen`).classList.add('active');
    }

    startTraining() {
        this.showScreen('game');
        this.resetSession();
        this.dealNewHand();
    }

    resetSession() {
        this.session = {
            hands: 0,
            moves: 0,
            score: 0,
            bestMoves: 0,
            correctMoves: 0,
            inaccuracies: 0,
            wrongMoves: 0,
            blunders: 0,
            totalEVLoss: 0,
            history: []
        };
        this.updateStats();
    }

    dealNewHand() {
        this.session.hands++;
        
        // Generate scenario
        const scenario = this.generateScenario();
        this.currentHand = scenario;
        
        // Calculate GTO strategy
        this.currentGTOStrategy = this.solver.getGTOStrategy(scenario.gameState);
        
        // Update UI
        this.renderHand();
        this.updateActionButtons();
        this.updateStats();
        this.clearFeedback();
    }

    generateScenario() {
        try {
            // Generate realistic poker scenario based on settings
            const positions = ['UTG', 'HJ', 'CO', 'BTN', 'SB', 'BB'];
            
            // For SRP (Single Raised Pot)
            let raiserPos, heroPos, preflopHistory;
            
            if (this.settings.preflopAction === 'srp') {
                // Random raiser from UTG, HJ, CO, BTN
                const raisingPositions = ['UTG', 'HJ', 'CO', 'BTN'];
                raiserPos = raisingPositions[Math.floor(Math.random() * raisingPositions.length)];
                
                // Hero is in a calling position
                const callingPositions = positions.slice(positions.indexOf(raiserPos) + 1);
                heroPos = callingPositions[Math.floor(Math.random() * callingPositions.length)];
                
                preflopHistory = `${raiserPos} opens, ${heroPos} calls`;
            } else {
                // Fallback for other action types
                raiserPos = 'UTG';
                heroPos = 'BB';
                preflopHistory = `${raiserPos} opens, ${heroPos} calls`;
            }
        
            // Generate hero hand from appropriate range
            const heroRange = this.ranges.getRange(heroPos, 'call', raiserPos);
            let heroHand = this.ranges.getRandomHandFromRange(heroRange);
            
            // Fallback if no valid hand
            if (!heroHand) {
                heroHand = [
                    { rank: 'A', suit: '♠' },
                    { rank: 'K', suit: '♥' }
                ];
            }
        
            // Generate flop
            let deck = this.engine.createDeck();
            deck = deck.filter(card => 
                !heroHand.some(h => h.rank === card.rank && h.suit === card.suit)
            );
            deck = this.engine.shuffle(deck);
            
            const board = deck.slice(0, 3);
        
            // Determine positions
            const isHeroIP = positions.indexOf(heroPos) > positions.indexOf(raiserPos);
            
            // Pot calculation (in bb)
            // Preflop: raiser opens 2.5bb, hero calls 2.5bb, blinds 1.5bb = 6.5bb pot
            const pot = 6.5;
            const stack = 100; // 100bb stacks
            
            // Determine action
            let action, betSize;
            if (isHeroIP) {
                // Villain is OOP and acts first
                // 70% of the time villain c-bets
                if (Math.random() < 0.7) {
                    action = 'facing_bet';
                    betSize = pot * (0.33 + Math.random() * 0.67); // 33-100% pot bet
                } else {
                    action = 'check_to_hero';
                    betSize = 0;
                }
            } else {
                // Hero is OOP and acts first
                action = 'open_action';
                betSize = 0;
            }
            
            return {
                heroHand,
                board,
                raiserPos,
                heroPos,
                preflopHistory,
                gameState: {
                    heroHand,
                    board,
                    pot,
                    stack,
                    position: heroPos,
                    villainPosition: raiserPos,
                    street: 'flop',
                    isHeroIP,
                    action,
                    betSize,
                    preflopAction: this.settings.preflopAction
                }
            };
        } catch (error) {
            console.error('Error generating scenario:', error);
            // Return a safe fallback scenario
            return {
                heroHand: [
                    { rank: 'A', suit: '♠' },
                    { rank: 'K', suit: '♥' }
                ],
                board: [
                    { rank: 'K', suit: '♦' },
                    { rank: '9', suit: '♠' },
                    { rank: '4', suit: '♣' }
                ],
                raiserPos: 'UTG',
                heroPos: 'BB',
                preflopHistory: 'UTG opens, BB calls',
                gameState: {
                    heroHand: [
                        { rank: 'A', suit: '♠' },
                        { rank: 'K', suit: '♥' }
                    ],
                    board: [
                        { rank: 'K', suit: '♦' },
                        { rank: '9', suit: '♠' },
                        { rank: '4', suit: '♣' }
                    ],
                    pot: 6.5,
                    stack: 100,
                    position: 'BB',
                    villainPosition: 'UTG',
                    street: 'flop',
                    isHeroIP: false,
                    action: 'open_action',
                    betSize: 0,
                    preflopAction: 'srp'
                }
            };
        }
    }

    renderHand() {
        const hand = this.currentHand;
        
        // Update hand number
        document.getElementById('current-hand-num').textContent = `Hand #${this.session.hands}`;
        document.getElementById('preflop-action-display').textContent = 
            `${this.settings.preflopAction.toUpperCase()} - ${hand.preflopHistory}`;
        
        // Render hero cards
        const heroHandEl = document.getElementById('hero-hand');
        heroHandEl.innerHTML = hand.heroHand.map(card => this.createCardElement(card)).join('');
        
        // Render board
        const boardEl = document.getElementById('board-cards');
        boardEl.innerHTML = hand.board.map(card => this.createCardElement(card)).join('');
        
        // Update pot
        document.getElementById('pot-size').textContent = `Pot: ${hand.gameState.pot.toFixed(1)} bb`;
        
        // Update position indicators
        document.querySelectorAll('.position-seat').forEach(el => {
            el.classList.remove('active');
        });
        document.getElementById(`position-${hand.raiserPos.toLowerCase()}`).classList.add('active');
        document.getElementById(`position-${hand.heroPos.toLowerCase()}`).classList.add('active');
    }

    createCardElement(card) {
        const suitClass = (card.suit === '♥' || card.suit === '♦') ? 'hearts' : 
                         (card.suit === '♠') ? 'spades' : 
                         (card.suit === '♦') ? 'diamonds' : 'clubs';
        
        return `
            <div class="card ${suitClass}">
                <div class="card-rank">${card.rank}</div>
                <div class="card-suit">${card.suit}</div>
            </div>
        `;
    }

    updateActionButtons() {
        const action = this.currentHand.gameState.action;
        const betSize = this.currentHand.gameState.betSize;
        const pot = this.currentHand.gameState.pot;
        
        const buttonsContainer = document.getElementById('action-buttons');
        buttonsContainer.innerHTML = '';
        
        if (action === 'facing_bet') {
            // Facing a bet: Fold, Call, Raise options
            buttonsContainer.innerHTML = `
                <button class="action-btn fold-btn" data-action="fold">
                    <span class="action-label">FOLD</span>
                </button>
                <button class="action-btn call-btn" data-action="call">
                    <span class="action-label">CALL ${betSize.toFixed(1)} bb</span>
                </button>
                <button class="action-btn raise-btn" data-action="raise" data-size="0.5">
                    <span class="action-label">RAISE 50%</span>
                </button>
                <button class="action-btn raise-btn" data-action="raise" data-size="0.67">
                    <span class="action-label">RAISE 67%</span>
                </button>
                <button class="action-btn raise-btn" data-action="raise" data-size="1.0">
                    <span class="action-label">RAISE POT</span>
                </button>
                <button class="action-btn raise-btn" data-action="raise" data-size="1.5">
                    <span class="action-label">RAISE 150%</span>
                </button>
            `;
        } else if (action === 'check_to_hero' || action === 'open_action') {
            // Hero acts first: Check/Bet options
            buttonsContainer.innerHTML = `
                <button class="action-btn fold-btn" data-action="check">
                    <span class="action-label">CHECK</span>
                </button>
                <button class="action-btn raise-btn" data-action="bet" data-size="0.33">
                    <span class="action-label">BET 33%</span>
                </button>
                <button class="action-btn raise-btn" data-action="bet" data-size="0.5">
                    <span class="action-label">BET 50%</span>
                </button>
                <button class="action-btn raise-btn" data-action="bet" data-size="0.67">
                    <span class="action-label">BET 67%</span>
                </button>
                <button class="action-btn raise-btn" data-action="bet" data-size="1.0">
                    <span class="action-label">BET POT</span>
                </button>
                <button class="action-btn raise-btn" data-action="bet" data-size="1.5">
                    <span class="action-label">BET 150%</span>
                </button>
            `;
        }
        
        // Reattach event listeners
        document.querySelectorAll('.action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                const size = parseFloat(e.currentTarget.dataset.size) || 0;
                this.handlePlayerAction(action, size);
            });
        });
    }

    handlePlayerAction(action, size) {
        this.session.moves++;
        
        // Convert action to strategy format
        const strategyAction = this.solver.convertButtonAction(action, size);
        
        // Evaluate action
        const evaluation = this.solver.evaluateAction(
            strategyAction,
            this.currentGTOStrategy.strategy
        );
        
        // Update statistics
        this.updateSessionStats(evaluation);
        
        // Show feedback
        this.showFeedback(action, size, evaluation);
        
        // Add to history
        this.addToHistory(evaluation);
        
        // Update display
        this.updateStats();
        
        // Deal next hand after delay
        setTimeout(() => {
            this.dealNewHand();
        }, 2500);
    }

    updateSessionStats(evaluation) {
        this.session.totalEVLoss += evaluation.evLoss;
        
        switch(evaluation.category) {
            case 'best':
                this.session.bestMoves++;
                break;
            case 'correct':
                this.session.correctMoves++;
                break;
            case 'inaccuracy':
                this.session.inaccuracies++;
                break;
            case 'wrong':
                this.session.wrongMoves++;
                break;
            case 'blunder':
                this.session.blunders++;
                break;
        }
        
        // Calculate score (0-100)
        const totalDecisions = this.session.bestMoves + this.session.correctMoves + 
                              this.session.inaccuracies + this.session.wrongMoves + 
                              this.session.blunders;
        
        if (totalDecisions > 0) {
            const weightedScore = (
                this.session.bestMoves * 100 +
                this.session.correctMoves * 80 +
                this.session.inaccuracies * 50 +
                this.session.wrongMoves * 20 +
                this.session.blunders * 0
            ) / totalDecisions;
            
            this.session.score = Math.round(weightedScore);
        }
    }

    showFeedback(action, size, evaluation) {
        const feedbackEl = document.getElementById('feedback-message');
        feedbackEl.className = `feedback-message ${evaluation.category}`;
        
        const actionLabel = this.solver.getActionLabel(
            this.solver.convertButtonAction(action, size)
        );
        const optimalLabel = this.solver.getActionLabel(evaluation.optimalAction);
        
        let message = '';
        
        if (evaluation.category === 'best') {
            message = `<strong>✓ Best Move!</strong><br>`;
            message += `${actionLabel} is the GTO play (${(evaluation.playerFrequency * 100).toFixed(1)}% frequency)`;
        } else if (evaluation.category === 'correct') {
            message = `<strong>✓ Correct Move</strong><br>`;
            message += `${actionLabel} is acceptable (${(evaluation.playerFrequency * 100).toFixed(1)}% frequency)<br>`;
            message += `Best: ${optimalLabel} (${(evaluation.optimalFrequency * 100).toFixed(1)}%)`;
        } else if (evaluation.category === 'inaccuracy') {
            message = `<strong>~ Inaccuracy</strong><br>`;
            message += `${actionLabel} is suboptimal. Better: ${optimalLabel}`;
        } else if (evaluation.category === 'wrong') {
            message = `<strong>✗ Wrong Move</strong><br>`;
            message += `${actionLabel} is incorrect. Should: ${optimalLabel}`;
        } else {
            message = `<strong>✗✗ Blunder!</strong><br>`;
            message += `${actionLabel} is a serious mistake. Should: ${optimalLabel}`;
        }
        
        message += `<div class="feedback-ev">EV Loss: ${evaluation.evLoss.toFixed(2)} bb</div>`;
        
        feedbackEl.innerHTML = message;
    }

    clearFeedback() {
        const feedbackEl = document.getElementById('feedback-message');
        feedbackEl.className = 'feedback-message';
        feedbackEl.innerHTML = '';
    }

    updateStats() {
        document.getElementById('stat-hands').textContent = this.session.hands;
        document.getElementById('stat-moves').textContent = this.session.moves;
        document.getElementById('stat-score').textContent = `${this.session.score}%`;
        
        document.getElementById('best-moves').textContent = this.session.bestMoves;
        document.getElementById('correct-moves').textContent = this.session.correctMoves;
        document.getElementById('inaccuracy-moves').textContent = this.session.inaccuracies;
        document.getElementById('wrong-moves').textContent = this.session.wrongMoves;
        document.getElementById('blunder-moves').textContent = this.session.blunders;
        
        document.getElementById('total-ev-loss').textContent = this.session.totalEVLoss.toFixed(2);
        const avgEVLoss = this.session.hands > 0 ? this.session.totalEVLoss / this.session.hands : 0;
        document.getElementById('avg-ev-loss').textContent = avgEVLoss.toFixed(2);
        
        // Update accuracy bar
        const accuracyFill = document.getElementById('accuracy-fill');
        accuracyFill.style.width = `${this.session.score}%`;
    }

    addToHistory(evaluation) {
        const hand = this.currentHand;
        const historyItem = {
            handNum: this.session.hands,
            heroHand: hand.heroHand,
            board: hand.board,
            category: evaluation.category,
            evaluation
        };
        
        this.session.history.unshift(historyItem);
        
        // Keep only last 20 hands
        if (this.session.history.length > 20) {
            this.session.history.pop();
        }
        
        this.renderHistory();
    }

    renderHistory() {
        const historyList = document.getElementById('history-list');
        historyList.innerHTML = '';
        
        this.session.history.forEach((item, index) => {
            const handStr = item.heroHand.map(c => `${c.rank}${this.getSuitSymbol(c.suit)}`).join('');
            const boardStr = item.board.map(c => `${c.rank}${this.getSuitSymbol(c.suit)}`).join(' ');
            
            const historyEl = document.createElement('div');
            historyEl.className = `history-item ${item.category}`;
            historyEl.innerHTML = `
                <div class="history-hand">Hand #${item.handNum}: ${handStr}</div>
                <div class="history-action">${boardStr} • ${item.category}</div>
            `;
            
            historyList.appendChild(historyEl);
        });
    }

    getSuitSymbol(suit) {
        const symbols = {
            '♠': 's',
            '♥': 'h',
            '♦': 'd',
            '♣': 'c'
        };
        return symbols[suit] || suit;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    try {
        console.log('Initializing GTO Poker Trainer...');
        console.log('Dependencies loaded:', {
            pokerEngine: typeof pokerEngine !== 'undefined',
            preflopRanges: typeof preflopRanges !== 'undefined',
            gtoSolver: typeof gtoSolver !== 'undefined'
        });
        
        const app = new PokerTrainer();
        window.pokerTrainer = app; // For debugging
        console.log('GTO Poker Trainer initialized successfully!');
    } catch (error) {
        console.error('Error initializing poker trainer:', error);
        alert('Error loading poker trainer. Please check the console for details.');
    }
});

