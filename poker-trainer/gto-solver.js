// GTO Solver - Postflop Decision Engine
// This implements simplified GTO strategies based on:
// - Hand strength and equity
// - Position
// - Stack depth
// - Board texture
// - Pot odds and expected value
// - Opponent ranges

class GTOSolver {
    constructor() {
        this.engine = pokerEngine;
        this.ranges = preflopRanges;
        
        // GTO frequencies and thresholds
        this.config = {
            // Value betting thresholds
            valueThreshold: 0.65,      // Hand strength to value bet
            thinValueThreshold: 0.55,  // Threshold for thin value
            
            // Bluffing frequencies (balanced ranges)
            bluffFrequency: 0.33,      // Bluff to value ratio
            
            // Continuation bet frequencies
            cBetFreqIP: 0.75,          // In position c-bet frequency
            cBetFreqOOP: 0.65,         // Out of position c-bet frequency
            
            // Defense frequencies (vs bet)
            minDefenseFreq: 0.67,      // Minimum defense frequency vs bet
            
            // Check-raise frequencies
            checkRaiseFreq: 0.12,      // Overall check-raise frequency
            
            // Bet sizing standards
            betSizes: {
                flop: {
                    small: 0.33,       // 33% pot
                    medium: 0.5,       // 50% pot  
                    standard: 0.67,    // 67% pot
                    large: 1.0,        // Pot
                    overbet: 1.5       // 150% pot
                },
                turn: {
                    small: 0.5,
                    medium: 0.67,
                    standard: 0.75,
                    large: 1.0,
                    overbet: 1.5
                },
                river: {
                    small: 0.5,
                    medium: 0.67,
                    standard: 0.75,
                    large: 1.0,
                    overbet: 1.5
                }
            }
        };
    }

    // Main decision function - returns GTO strategy
    getGTOStrategy(gameState) {
        const {
            heroHand,
            board,
            pot,
            stack,
            position,
            villainPosition,
            street,
            isHeroIP,
            action, // 'facing_bet', 'facing_raise', 'check_to_hero', 'open_action'
            betSize,
            preflopAction
        } = gameState;

        // Calculate hand metrics
        const handStrength = this.engine.calculateHandStrength(heroHand, board);
        const drawStrength = this.engine.calculateDrawStrength(heroHand, board);
        const boardTexture = this.engine.analyzeBoardTexture(board);
        const equity = this.calculateApproximateEquity(heroHand, board, villainPosition, preflopAction);
        
        // Build strategy based on action type
        let strategy = {};
        
        if (action === 'facing_bet') {
            strategy = this.getFacingBetStrategy(
                handStrength, equity, drawStrength, boardTexture,
                betSize, pot, isHeroIP, street
            );
        } else if (action === 'facing_raise') {
            strategy = this.getFacingRaiseStrategy(
                handStrength, equity, boardTexture,
                betSize, pot, isHeroIP
            );
        } else if (action === 'check_to_hero') {
            strategy = this.getCheckToHeroStrategy(
                handStrength, equity, drawStrength, boardTexture,
                pot, stack, isHeroIP, street, villainPosition
            );
        } else if (action === 'open_action') {
            strategy = this.getOpenActionStrategy(
                handStrength, equity, drawStrength, boardTexture,
                pot, stack, isHeroIP, street, villainPosition
            );
        }
        
        return {
            strategy,
            metrics: {
                handStrength,
                equity,
                drawStrength,
                boardTexture
            }
        };
    }

    // Strategy when facing a bet
    getFacingBetStrategy(handStrength, equity, drawStrength, boardTexture, betSize, pot, isHeroIP, street) {
        const strategy = {
            fold: 0,
            call: 0,
            raise_0.33: 0,
            raise_0.5: 0,
            raise_0.67: 0,
            raise_1.0: 0,
            raise_1.5: 0
        };
        
        const potOdds = betSize / (pot + betSize);
        const requiredEquity = potOdds;
        
        // Strong hands - raise for value
        if (handStrength >= 0.75 || (handStrength >= 0.7 && isHeroIP)) {
            strategy.raise_0.67 = 0.4;
            strategy.raise_1.0 = 0.4;
            strategy.call = 0.15; // Slowplay sometimes
            strategy.fold = 0.05; // Rarely fold
        }
        // Good hands - call or raise
        else if (handStrength >= 0.6 || equity >= 0.6) {
            if (isHeroIP) {
                strategy.raise_0.5 = 0.25;
                strategy.raise_0.67 = 0.15;
                strategy.call = 0.55;
                strategy.fold = 0.05;
            } else {
                strategy.call = 0.75;
                strategy.raise_0.67 = 0.15;
                strategy.fold = 0.1;
            }
        }
        // Medium hands - mostly call, some bluff raises
        else if (handStrength >= 0.45 || equity >= requiredEquity + 0.1) {
            strategy.call = 0.7;
            strategy.fold = 0.25;
            // Occasional bluff raise with good blockers
            if (boardTexture.flushDraw || boardTexture.connected) {
                strategy.raise_0.67 = 0.05;
            }
        }
        // Draws - call if odds are good
        else if (drawStrength >= 0.25 && equity >= requiredEquity) {
            strategy.call = 0.75;
            strategy.fold = 0.2;
            // Semi-bluff raise with strong draws
            if (drawStrength >= 0.35) {
                strategy.raise_0.67 = 0.05;
            }
        }
        // Weak hands - fold mostly, occasional bluffs
        else if (equity >= requiredEquity * 0.8) {
            strategy.fold = 0.85;
            strategy.call = 0.1;
            // Bluff with blockers on right boards
            if (!boardTexture.paired && (boardTexture.flushDraw || boardTexture.connected)) {
                strategy.raise_1.0 = 0.05;
            }
        }
        // Very weak hands - fold
        else {
            strategy.fold = 1.0;
        }
        
        return this.normalizeStrategy(strategy);
    }

    // Strategy when facing a raise
    getFacingRaiseStrategy(handStrength, equity, boardTexture, betSize, pot, isHeroIP) {
        const strategy = {
            fold: 0,
            call: 0,
            raise_1.0: 0,
            raise_1.5: 0
        };
        
        // Very strong hands - 3-bet or call
        if (handStrength >= 0.8) {
            strategy.raise_1.5 = 0.5;
            strategy.call = 0.45;
            strategy.fold = 0.05;
        }
        // Strong hands - mostly call
        else if (handStrength >= 0.65) {
            strategy.call = 0.8;
            strategy.raise_1.0 = 0.15;
            strategy.fold = 0.05;
        }
        // Medium-strong hands
        else if (handStrength >= 0.5 || equity >= 0.55) {
            strategy.call = 0.6;
            strategy.fold = 0.4;
        }
        // Bluff catchers and draws
        else if (equity >= 0.4) {
            strategy.call = 0.3;
            strategy.fold = 0.7;
        }
        // Weak hands
        else {
            strategy.fold = 1.0;
        }
        
        return this.normalizeStrategy(strategy);
    }

    // Strategy when checked to hero
    getCheckToHeroStrategy(handStrength, equity, drawStrength, boardTexture, pot, stack, isHeroIP, street, villainPosition) {
        const strategy = {
            check: 0,
            bet_0.33: 0,
            bet_0.5: 0,
            bet_0.67: 0,
            bet_1.0: 0,
            bet_1.5: 0
        };
        
        const betSizes = this.config.betSizes[street] || this.config.betSizes.flop;
        
        // Very strong hands - bet for value or check for deception
        if (handStrength >= 0.8) {
            strategy.bet_0.67 = 0.3;
            strategy.bet_1.0 = 0.4;
            strategy.check = 0.3; // Check to induce bluffs
        }
        // Strong hands - bet for value
        else if (handStrength >= 0.65) {
            strategy.bet_0.5 = 0.3;
            strategy.bet_0.67 = 0.5;
            strategy.check = 0.2;
        }
        // Medium-strong hands - bet medium or check
        else if (handStrength >= 0.5) {
            strategy.bet_0.33 = 0.3;
            strategy.bet_0.5 = 0.35;
            strategy.check = 0.35;
        }
        // Medium hands and draws
        else if (handStrength >= 0.35 || drawStrength >= 0.2) {
            if (isHeroIP) {
                // More aggression in position
                strategy.bet_0.33 = 0.4;
                strategy.bet_0.5 = 0.2;
                strategy.check = 0.4;
            } else {
                // More checking out of position
                strategy.check = 0.7;
                strategy.bet_0.33 = 0.2;
                strategy.bet_0.5 = 0.1;
            }
        }
        // Weak hands - bluff or check
        else {
            if (boardTexture.wetness > 0.6 && isHeroIP) {
                // Good bluffing board
                strategy.bet_0.67 = 0.2;
                strategy.bet_0.5 = 0.15;
                strategy.check = 0.65;
            } else {
                strategy.check = 0.9;
                strategy.bet_0.5 = 0.1;
            }
        }
        
        return this.normalizeStrategy(strategy);
    }

    // Strategy for open action (c-bet scenario)
    getOpenActionStrategy(handStrength, equity, drawStrength, boardTexture, pot, stack, isHeroIP, street, villainPosition) {
        const strategy = {
            check: 0,
            bet_0.33: 0,
            bet_0.5: 0,
            bet_0.67: 0,
            bet_1.0: 0
        };
        
        const cBetFreq = isHeroIP ? this.config.cBetFreqIP : this.config.cBetFreqOOP;
        
        // Strong hands - almost always bet
        if (handStrength >= 0.7) {
            strategy.bet_0.67 = 0.5;
            strategy.bet_1.0 = 0.3;
            strategy.bet_0.5 = 0.15;
            strategy.check = 0.05;
        }
        // Good hands - bet frequently
        else if (handStrength >= 0.55) {
            strategy.bet_0.5 = 0.4;
            strategy.bet_0.67 = 0.35;
            strategy.check = 0.25;
        }
        // Medium hands - bet on good boards
        else if (handStrength >= 0.4 || drawStrength >= 0.2) {
            if (boardTexture.wetness < 0.5 || isHeroIP) {
                strategy.bet_0.33 = 0.35;
                strategy.bet_0.5 = 0.3;
                strategy.check = 0.35;
            } else {
                strategy.check = 0.6;
                strategy.bet_0.33 = 0.25;
                strategy.bet_0.5 = 0.15;
            }
        }
        // Weak hands - occasional bluffs
        else {
            const shouldBluff = Math.random() < (cBetFreq - 0.5); // Bluff to maintain frequency
            if (shouldBluff && (boardTexture.wetness > 0.6 || !boardTexture.paired)) {
                strategy.bet_0.67 = 0.2;
                strategy.bet_0.5 = 0.15;
                strategy.check = 0.65;
            } else {
                strategy.check = 0.85;
                strategy.bet_0.33 = 0.1;
                strategy.bet_0.5 = 0.05;
            }
        }
        
        return this.normalizeStrategy(strategy);
    }

    // Normalize strategy to sum to 1.0
    normalizeStrategy(strategy) {
        const total = Object.values(strategy).reduce((a, b) => a + b, 0);
        if (total === 0) return strategy;
        
        const normalized = {};
        for (let action in strategy) {
            normalized[action] = strategy[action] / total;
        }
        return normalized;
    }

    // Get the GTO action (probabilistically sampled from strategy)
    getGTOAction(strategy) {
        const rand = Math.random();
        let cumulative = 0;
        
        for (let action in strategy) {
            cumulative += strategy[action];
            if (rand <= cumulative) {
                return action;
            }
        }
        
        // Fallback to highest frequency action
        return Object.keys(strategy).reduce((a, b) => 
            strategy[a] > strategy[b] ? a : b
        );
    }

    // Evaluate player action vs GTO
    evaluateAction(playerAction, gtoStrategy) {
        const playerFreq = gtoStrategy[playerAction] || 0;
        
        // Calculate EV loss (simplified)
        let maxFreq = Math.max(...Object.values(gtoStrategy));
        let evLoss = 0;
        let category = '';
        
        // Best move: within 5% of max frequency
        if (playerFreq >= maxFreq - 0.05) {
            category = 'best';
            evLoss = 0;
        }
        // Correct move: frequency > 20%
        else if (playerFreq >= 0.20) {
            category = 'correct';
            evLoss = (maxFreq - playerFreq) * 0.1;
        }
        // Inaccuracy: frequency 10-20%
        else if (playerFreq >= 0.10) {
            category = 'inaccuracy';
            evLoss = (maxFreq - playerFreq) * 0.25;
        }
        // Wrong move: frequency 5-10%
        else if (playerFreq >= 0.05) {
            category = 'wrong';
            evLoss = (maxFreq - playerFreq) * 0.5;
        }
        // Blunder: frequency < 5%
        else {
            category = 'blunder';
            evLoss = 1.0;
        }
        
        return {
            category,
            evLoss,
            playerFrequency: playerFreq,
            optimalAction: Object.keys(gtoStrategy).reduce((a, b) => 
                gtoStrategy[a] > gtoStrategy[b] ? a : b
            ),
            optimalFrequency: maxFreq,
            allFrequencies: gtoStrategy
        };
    }

    // Approximate equity calculation (faster than Monte Carlo)
    calculateApproximateEquity(heroHand, board, villainPosition, preflopAction) {
        // Use simplified equity calculation based on hand strength
        // In production, this would use precomputed equity tables
        
        const handStrength = this.engine.calculateHandStrength(heroHand, board);
        const drawStrength = this.engine.calculateDrawStrength(heroHand, board);
        
        // Combine hand strength and draw potential
        let equity = handStrength * 0.7 + drawStrength * 0.3;
        
        // Adjust based on board texture
        const boardTexture = this.engine.analyzeBoardTexture(board);
        if (boardTexture.wetness > 0.7) {
            equity *= 0.95; // Slightly reduce on wet boards (more uncertainty)
        }
        
        return Math.max(0.1, Math.min(0.9, equity));
    }

    // Get action label for display
    getActionLabel(action) {
        if (action === 'fold') return 'FOLD';
        if (action === 'call') return 'CALL';
        if (action === 'check') return 'CHECK';
        if (action.startsWith('bet_')) {
            const size = parseFloat(action.split('_')[1]);
            return `BET ${Math.round(size * 100)}%`;
        }
        if (action.startsWith('raise_')) {
            const size = parseFloat(action.split('_')[1]);
            return `RAISE ${Math.round(size * 100)}%`;
        }
        return action.toUpperCase();
    }

    // Convert action button to strategy action format
    convertButtonAction(buttonAction, buttonSize) {
        if (buttonAction === 'fold') return 'fold';
        if (buttonAction === 'call') return 'call';
        if (buttonAction === 'check') return 'check';
        if (buttonAction === 'raise' || buttonAction === 'bet') {
            return `${buttonAction}_${buttonSize}`;
        }
        return buttonAction;
    }

    // Get recommended bet sizes for a situation
    getRecommendedBetSizes(handStrength, boardTexture, street, isHeroIP) {
        const sizes = [];
        
        // Strong hands - medium to large bets
        if (handStrength >= 0.7) {
            sizes.push(0.67, 1.0);
            if (boardTexture.wetness > 0.6) sizes.push(1.5);
        }
        // Medium hands - small to medium
        else if (handStrength >= 0.5) {
            sizes.push(0.33, 0.5, 0.67);
        }
        // Weak hands / bluffs - polarized (small or large)
        else {
            sizes.push(0.33, 0.67);
            if (boardTexture.wetness > 0.7) sizes.push(1.0);
        }
        
        return sizes;
    }
}

const gtoSolver = new GTOSolver();

