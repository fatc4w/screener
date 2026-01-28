// Advanced GTO Solver - Production-Quality Decision Engine
// Implements sophisticated GTO strategies based on extensive solver studies

class AdvancedGTOSolver {
    constructor() {
        // Delay initialization until dependencies are loaded
        this.engine = null;
        this.ranges = null;
        
        // Comprehensive GTO configuration based on solver research
        this.config = {
            // Equity thresholds for different hand categories
            equity: {
                nuts: 0.95,           // Near-unbeatable hands
                veryStrong: 0.85,     // Very strong value hands
                strong: 0.70,         // Strong value hands
                mediumStrong: 0.60,   // Medium-strong value/thin value
                medium: 0.50,         // Medium hands (bluff catchers)
                marginal: 0.40,       // Marginal hands
                weak: 0.30            // Weak hands/air
            },
            
            // C-bet frequencies by board texture and position
            cBetFrequencies: {
                // In Position
                IP: {
                    dry: 0.85,        // Very high on dry boards (K72r, A94r)
                    medium: 0.75,     // Standard
                    wet: 0.65,        // Lower on wet boards (JT8ss, 876ss)
                    paired: 0.70      // Moderate on paired boards
                },
                // Out of Position
                OOP: {
                    dry: 0.70,
                    medium: 0.60,
                    wet: 0.50,
                    paired: 0.55
                }
            },
            
            // Defense frequencies vs different bet sizes
            defenseFrequencies: {
                small: 0.75,      // vs 33% pot bet (need to defend 75%)
                medium: 0.67,     // vs 50% pot bet
                standard: 0.60,   // vs 67% pot bet
                pot: 0.50,        // vs 100% pot bet
                overbet: 0.40     // vs 150% pot bet
            },
            
            // Check-raise frequencies by position and board
            checkRaiseFreq: {
                OOP_wet: 0.15,
                OOP_dry: 0.08,
                OOP_paired: 0.12,
                IP: 0.05  // Very rare IP
            },
            
            // Optimal bet sizing by street and hand strength
            optimalSizing: {
                flop: {
                    polarized: [0.75, 1.0],     // Nuts + bluffs
                    merged: [0.33, 0.5, 0.67],  // Mixed range
                    protection: [0.5, 0.67]     // Vulnerable hands
                },
                turn: {
                    polarized: [0.67, 1.0, 1.5],
                    merged: [0.5, 0.67],
                    protection: [0.67, 0.75]
                },
                river: {
                    polarized: [0.75, 1.0, 1.5],  // Often overbet
                    thinValue: [0.5, 0.67],
                    bluff: [0.75, 1.0]
                }
            },
            
            // Range advantage thresholds
            rangeAdvantage: {
                huge: 0.20,      // 20%+ equity advantage
                significant: 0.12,
                moderate: 0.07,
                small: 0.03
            }
        };
        
        // Precomputed equity tables for common situations (speeds up calculations)
        this.equityTables = this.initializeEquityTables();
    }

    // Initialize equity lookup tables for common hand categories
    initializeEquityTables() {
        return {
            // Overpair vs typical calling range on various board textures
            overpairEquity: {
                dry: 0.82,
                medium: 0.78,
                wet: 0.72,
                paired: 0.85
            },
            // Top pair vs calling range
            topPairEquity: {
                dry: 0.68,
                medium: 0.63,
                wet: 0.58,
                paired: 0.70
            },
            // Middle pair
            middlePairEquity: {
                dry: 0.52,
                medium: 0.48,
                wet: 0.42,
                paired: 0.48
            },
            // Flush draw
            flushDrawEquity: {
                made: 0.95,
                nineOuts: 0.36,  // 9-out flush draw on flop
                twelveOuts: 0.45  // Flush draw + overcards
            },
            // Open-ended straight draw
            oesd: {
                clean: 0.32,  // Clean 8-outer
                combo: 0.50   // OESD + overcard or pair
            }
        };
    }

    // Initialize engine and ranges if not already done
    initialize() {
        if (!this.engine && typeof pokerEngine !== 'undefined') {
            this.engine = pokerEngine;
        }
        if (!this.ranges && typeof preflopRanges !== 'undefined') {
            this.ranges = preflopRanges;
        }
    }

    // Main GTO strategy calculation (much more sophisticated)
    getGTOStrategy(gameState) {
        this.initialize();
        
        const {
            heroHand, board, pot, stack, position, villainPosition,
            street, isHeroIP, action, betSize, preflopAction
        } = gameState;

        // Calculate comprehensive hand metrics
        const metrics = this.calculateComprehensiveMetrics(heroHand, board, villainPosition, preflopAction);
        
        // Determine range advantage
        const rangeAdvantage = this.calculateRangeAdvantage(
            position, villainPosition, board, preflopAction
        );
        
        // Build strategy based on action type
        let strategy = {};
        
        switch(action) {
            case 'facing_bet':
                strategy = this.getAdvancedFacingBetStrategy(
                    metrics, betSize, pot, isHeroIP, street, rangeAdvantage
                );
                break;
            case 'facing_raise':
                strategy = this.getAdvancedFacingRaiseStrategy(
                    metrics, betSize, pot, isHeroIP, rangeAdvantage
                );
                break;
            case 'check_to_hero':
                strategy = this.getAdvancedCheckToHeroStrategy(
                    metrics, pot, stack, isHeroIP, street, rangeAdvantage
                );
                break;
            case 'open_action':
                strategy = this.getAdvancedOpenActionStrategy(
                    metrics, pot, stack, isHeroIP, street, villainPosition, rangeAdvantage
                );
                break;
        }
        
        return {
            strategy: this.normalizeStrategy(strategy),
            metrics,
            rangeAdvantage
        };
    }

    // Calculate comprehensive hand metrics
    calculateComprehensiveMetrics(heroHand, board, villainPosition, preflopAction) {
        const handStrength = this.engine.calculateHandStrength(heroHand, board);
        const boardTexture = this.analyzeAdvancedBoardTexture(board);
        
        // More accurate equity calculation
        const equity = this.calculateAccurateEquity(
            heroHand, board, boardTexture, villainPosition, preflopAction
        );
        
        // Detailed draw analysis
        const draws = this.analyzeDraws(heroHand, board);
        
        // Hand category classification
        const handCategory = this.classifyHand(heroHand, board, equity);
        
        // Blocker effects
        const blockers = this.analyzeBlockers(heroHand, board, boardTexture);
        
        return {
            handStrength,
            equity,
            boardTexture,
            draws,
            handCategory,
            blockers
        };
    }

    // Advanced board texture analysis
    analyzeAdvancedBoardTexture(board) {
        if (board.length < 3) return { type: 'preflop' };
        
        const ranks = board.map(c => this.engine.rankValues[c.rank]);
        const suits = board.map(c => c.suit);
        const sortedRanks = [...ranks].sort((a, b) => b - a);
        
        // Rank analysis
        const rankCounts = {};
        ranks.forEach(r => rankCounts[r] = (rankCounts[r] || 0) + 1);
        const uniqueRanks = Object.keys(rankCounts).length;
        const paired = uniqueRanks < board.length;
        const trips = Object.values(rankCounts).some(c => c >= 3);
        
        // Suit analysis
        const suitCounts = {};
        suits.forEach(s => suitCounts[s] = (suitCounts[s] || 0) + 1);
        const maxSuitCount = Math.max(...Object.values(suitCounts));
        const flushDraw = maxSuitCount >= 3;
        const flushPossible = maxSuitCount >= 3;
        const monochrome = maxSuitCount === 3;
        const twoTone = Object.keys(suitCounts).length === 2;
        const rainbow = Object.keys(suitCounts).length === 3;
        
        // Connectivity analysis (straight possibilities)
        const gaps = [];
        for (let i = 0; i < sortedRanks.length - 1; i++) {
            gaps.push(sortedRanks[i] - sortedRanks[i + 1]);
        }
        const maxGap = Math.max(...gaps);
        const minGap = Math.min(...gaps);
        
        const connected = maxGap <= 2;
        const doubleConnected = gaps.every(g => g <= 2);
        const straightPossible = maxGap <= 4;
        
        // High card content
        const highCards = ranks.filter(r => r >= 10).length;
        const broadway = ranks.every(r => r >= 10);
        const lowBoard = ranks.every(r => r <= 9);
        
        // Ace presence
        const hasAce = ranks.includes(14);
        
        // Texture classification
        let type = 'medium';
        let wetness = 0.4; // Base wetness
        
        // Adjust wetness based on features
        if (flushDraw) wetness += 0.20;
        if (connected) wetness += 0.18;
        if (doubleConnected) wetness += 0.12;
        if (paired) wetness -= 0.10; // Paired boards slightly drier
        if (trips) wetness -= 0.15;
        if (highCards >= 2) wetness += 0.10;
        if (broadway) wetness += 0.12;
        if (lowBoard && !connected) wetness -= 0.20; // Low disconnected very dry
        if (rainbow && maxGap > 4) wetness -= 0.18; // Rainbow + disconnected = dry
        
        wetness = Math.max(0, Math.min(1, wetness));
        
        // Classify board type
        if (wetness >= 0.7) type = 'wet';
        else if (wetness <= 0.35) type = 'dry';
        else type = 'medium';
        
        // Special cases
        if (trips) type = 'paired';
        if (paired && !trips) type = 'paired';
        
        return {
            type,
            wetness,
            ranks: sortedRanks,
            paired,
            trips,
            flushDraw,
            flushPossible,
            monochrome,
            twoTone,
            rainbow,
            connected,
            doubleConnected,
            straightPossible,
            highCards,
            broadway,
            lowBoard,
            hasAce,
            maxGap,
            minGap,
            uniqueRanks
        };
    }

    // More accurate equity calculation using board texture and ranges
    calculateAccurateEquity(heroHand, board, boardTexture, villainPosition, preflopAction) {
        const evaluation = this.engine.evaluateHand([...heroHand, ...board]);
        const handStrength = evaluation.rank / 8 + evaluation.value / 100000;
        
        // Get hand category
        const heroRanks = heroHand.map(c => this.engine.rankValues[c.rank]);
        const boardRanks = board.map(c => this.engine.rankValues[c.rank]);
        const topBoardCard = Math.max(...boardRanks);
        
        // Classify hero hand relative to board
        let category = 'unknown';
        let baseEquity = 0.5;
        
        // Overpair (pocket pair higher than board)
        if (heroRanks[0] === heroRanks[1] && heroRanks[0] > topBoardCard) {
            category = 'overpair';
            baseEquity = this.equityTables.overpairEquity[boardTexture.type] || 0.78;
        }
        // Top pair
        else if (Math.max(...heroRanks) === topBoardCard && evaluation.rank >= 1) {
            category = 'topPair';
            baseEquity = this.equityTables.topPairEquity[boardTexture.type] || 0.63;
            
            // Adjust for kicker
            const kickerRank = Math.min(...heroRanks);
            if (kickerRank >= 11) baseEquity += 0.05; // Good kicker
            else if (kickerRank <= 7) baseEquity -= 0.05; // Weak kicker
        }
        // Pocket pair (no match to board)
        else if (heroRanks[0] === heroRanks[1]) {
            if (heroRanks[0] >= 10) {
                category = 'underpair';
                baseEquity = 0.55;
            } else {
                category = 'smallPair';
                baseEquity = 0.42;
            }
        }
        // Two pair or better
        else if (evaluation.rank >= 2) {
            category = 'twoPairPlus';
            baseEquity = 0.80 + (evaluation.rank - 2) * 0.05;
        }
        // Draw analysis
        else {
            const draws = this.analyzeDraws(heroHand, board);
            if (draws.flushDraw) {
                baseEquity = this.equityTables.flushDrawEquity.nineOuts;
                if (draws.overcard) baseEquity += 0.08;
            } else if (draws.straightDraw) {
                baseEquity = this.equityTables.oesd.clean;
                if (draws.overcard) baseEquity += 0.08;
            } else if (draws.gutshot) {
                baseEquity = 0.18;
            } else {
                // No pair, no draw
                baseEquity = 0.35;
                if (Math.max(...heroRanks) >= 13) baseEquity += 0.05; // Ace high
            }
        }
        
        // Adjust for board texture
        if (boardTexture.wetness > 0.7) {
            baseEquity *= 0.95; // Reduce equity on wet boards (more uncertainty)
        }
        if (boardTexture.wetness < 0.4) {
            baseEquity *= 1.05; // Increase on dry boards (less draws)
        }
        
        return Math.max(0.05, Math.min(0.95, baseEquity));
    }

    // Analyze draws comprehensively
    analyzeDraws(heroHand, board) {
        const heroSuits = heroHand.map(c => c.suit);
        const boardSuits = board.map(c => c.suit);
        const heroRanks = heroHand.map(c => this.engine.rankValues[c.rank]);
        const boardRanks = board.map(c => this.engine.rankValues[c.rank]);
        
        // Flush draw
        const suitCounts = {};
        [...heroSuits, ...boardSuits].forEach(s => suitCounts[s] = (suitCounts[s] || 0) + 1);
        const flushDraw = Object.values(suitCounts).some(c => c >= 4);
        
        // Straight draw
        const allRanks = [...heroRanks, ...boardRanks].sort((a, b) => b - a);
        let straightDraw = false;
        let gutshot = false;
        
        // Check for straight possibilities
        const uniqueRanks = [...new Set(allRanks)];
        for (let i = 0; i < uniqueRanks.length - 3; i++) {
            const span = uniqueRanks[i] - uniqueRanks[i + 3];
            if (span === 3) {
                straightDraw = true; // OESD or better
            } else if (span === 4) {
                gutshot = true;
            }
        }
        
        // Overcard draw
        const topBoardRank = Math.max(...boardRanks);
        const overcard = heroRanks.some(r => r > topBoardRank);
        
        // Backdoor draws (2 to flush/straight)
        const backdoorFlush = Object.values(suitCounts).some(c => c === 3);
        
        return {
            flushDraw,
            straightDraw,
            gutshot,
            overcard,
            backdoorFlush,
            comboDraws: (flushDraw && straightDraw),
            strongDraw: (flushDraw || straightDraw),
            totalOuts: (flushDraw ? 9 : 0) + (straightDraw ? 8 : 0) + (gutshot ? 4 : 0) + (overcard ? 3 : 0)
        };
    }

    // Classify hand into GTO categories
    classifyHand(heroHand, board, equity) {
        if (equity >= this.config.equity.nuts) return 'nuts';
        if (equity >= this.config.equity.veryStrong) return 'veryStrong';
        if (equity >= this.config.equity.strong) return 'strong';
        if (equity >= this.config.equity.mediumStrong) return 'mediumStrong';
        if (equity >= this.config.equity.medium) return 'medium';
        if (equity >= this.config.equity.marginal) return 'marginal';
        return 'weak';
    }

    // Analyze blocker effects (critical for GTO)
    analyzeBlockers(heroHand, board, boardTexture) {
        const heroRanks = heroHand.map(c => c.rank);
        const heroSuits = heroHand.map(c => c.suit);
        
        // Ace blocker (blocks AA, AK, AQ, AJ, AT)
        const aceBlocker = heroRanks.includes('A');
        
        // King blocker
        const kingBlocker = heroRanks.includes('K');
        
        // Flush blocker (if board has flush draw)
        let flushBlocker = false;
        if (boardTexture.flushDraw) {
            const boardSuits = board.map(c => c.suit);
            const dominantSuit = boardSuits.reduce((acc, s) => {
                acc[s] = (acc[s] || 0) + 1;
                return acc;
            }, {});
            const flushSuit = Object.keys(dominantSuit).find(s => dominantSuit[s] >= 2);
            flushBlocker = heroSuits.includes(flushSuit);
        }
        
        // Straight blocker
        const straightBlocker = boardTexture.connected;
        
        return {
            aceBlocker,
            kingBlocker,
            flushBlocker,
            straightBlocker,
            strongBlocker: aceBlocker || (flushBlocker && boardTexture.flushDraw)
        };
    }

    // Calculate range advantage (who has more nutted hands)
    calculateRangeAdvantage(position, villainPosition, board, preflopAction) {
        const boardTexture = this.analyzeAdvancedBoardTexture(board);
        const topCard = Math.max(...board.map(c => this.engine.rankValues[c.rank]));
        
        let advantage = 0; // 0 = neutral, + = hero advantage, - = villain advantage
        
        // High card boards favor preflop raiser
        if (boardTexture.highCards >= 2) {
            if (preflopAction === 'srp') {
                advantage -= 0.10; // Raiser has range advantage on high boards
            }
        }
        
        // Low boards favor caller (has more small pairs)
        if (boardTexture.lowBoard) {
            advantage += 0.08;
        }
        
        // Flush draw boards are more neutral
        if (boardTexture.flushDraw) {
            advantage += 0.02;
        }
        
        // Connected boards favor suited connectors (both ranges have them)
        if (boardTexture.connected) {
            advantage += 0.03;
        }
        
        // Position gives inherent advantage
        const positions = ['UTG', 'HJ', 'CO', 'BTN', 'SB', 'BB'];
        const heroIdx = positions.indexOf(position);
        const villainIdx = positions.indexOf(villainPosition);
        if (heroIdx > villainIdx) advantage += 0.05;
        
        return {
            value: advantage,
            description: advantage > 0.10 ? 'significant hero' :
                        advantage > 0.05 ? 'moderate hero' :
                        advantage < -0.10 ? 'significant villain' :
                        advantage < -0.05 ? 'moderate villain' : 'neutral'
        };
    }

    // Advanced strategy when facing a bet
    getAdvancedFacingBetStrategy(metrics, betSize, pot, isHeroIP, street, rangeAdvantage) {
        const { equity, handCategory, draws, blockers, boardTexture } = metrics;
        const strategy = {
            fold: 0, call: 0,
            raise_0.33: 0, raise_0.5: 0, raise_0.67: 0, raise_1.0: 0, raise_1.5: 0
        };
        
        // Calculate pot odds and required equity
        const potOdds = betSize / (pot + betSize + betSize);
        const mdf = pot / (pot + betSize); // Minimum defense frequency
        
        // Nuts and very strong hands - mostly raise
        if (handCategory === 'nuts' || handCategory === 'veryStrong') {
            strategy.raise_1.0 = 0.45;
            strategy.raise_0.67 = 0.35;
            strategy.call = 0.15; // Slowplay sometimes
            strategy.fold = 0.05;
        }
        // Strong hands - mix of raise and call
        else if (handCategory === 'strong') {
            if (isHeroIP) {
                strategy.raise_0.67 = 0.35;
                strategy.raise_1.0 = 0.25;
                strategy.call = 0.35;
                strategy.fold = 0.05;
            } else {
                strategy.call = 0.60;
                strategy.raise_0.67 = 0.25;
                strategy.raise_1.0 = 0.10;
                strategy.fold = 0.05;
            }
        }
        // Medium-strong hands - mostly call, occasional raise
        else if (handCategory === 'mediumStrong') {
            strategy.call = 0.70;
            strategy.fold = 0.20;
            strategy.raise_0.67 = 0.10;
        }
        // Medium hands (bluff catchers) - call or fold based on odds
        else if (handCategory === 'medium') {
            if (equity >= potOdds + 0.05) {
                strategy.call = 0.65;
                strategy.fold = 0.35;
            } else {
                strategy.call = 0.40;
                strategy.fold = 0.60;
            }
        }
        // Draws - call if odds are good, sometimes semi-bluff
        else if (draws.strongDraw) {
            const drawEquity = draws.totalOuts / 47; // Approximate
            if (drawEquity >= potOdds) {
                strategy.call = 0.70;
                if (draws.comboDraws) {
                    strategy.raise_0.67 = 0.20; // Semi-bluff with combo draws
                }
                strategy.fold = 0.10;
            } else {
                strategy.call = 0.40;
                strategy.fold = 0.60;
            }
        }
        // Marginal hands - mostly fold, some bluff raises with blockers
        else if (handCategory === 'marginal') {
            strategy.fold = 0.75;
            strategy.call = 0.20;
            if (blockers.strongBlocker && boardTexture.wetness > 0.6) {
                strategy.raise_1.0 = 0.05; // Bluff with blockers
            }
        }
        // Weak hands - mostly fold, occasional bluff
        else {
            strategy.fold = 0.90;
            if (blockers.aceBlocker && boardTexture.flushDraw && !boardTexture.paired) {
                strategy.raise_1.0 = 0.08; // Bluff with ace blocker on flush boards
                strategy.fold = 0.82;
            }
            strategy.call = 0.02;
        }
        
        return strategy;
    }

    // Advanced strategy when facing a raise
    getAdvancedFacingRaiseStrategy(metrics, betSize, pot, isHeroIP, rangeAdvantage) {
        const { equity, handCategory } = metrics;
        const strategy = { fold: 0, call: 0, raise_1.0: 0, raise_1.5: 0 };
        
        // Against raises, range tightens significantly
        if (handCategory === 'nuts' || handCategory === 'veryStrong') {
            strategy.raise_1.5 = 0.40;
            strategy.call = 0.50;
            strategy.fold = 0.10;
        } else if (handCategory === 'strong') {
            strategy.call = 0.75;
            strategy.raise_1.0 = 0.15;
            strategy.fold = 0.10;
        } else if (handCategory === 'mediumStrong') {
            strategy.call = 0.55;
            strategy.fold = 0.45;
        } else if (equity >= 0.50) {
            strategy.call = 0.35;
            strategy.fold = 0.65;
        } else {
            strategy.fold = 0.95;
            strategy.call = 0.05;
        }
        
        return strategy;
    }

    // Advanced strategy when checked to
    getAdvancedCheckToHeroStrategy(metrics, pot, stack, isHeroIP, street, rangeAdvantage) {
        const { equity, handCategory, draws, boardTexture } = metrics;
        const strategy = {
            check: 0, bet_0.33: 0, bet_0.5: 0, bet_0.67: 0, bet_1.0: 0, bet_1.5: 0
        };
        
        // When villain checks, we have betting initiative
        
        // Nuts - bet big or check to trap
        if (handCategory === 'nuts') {
            strategy.bet_1.0 = 0.40;
            strategy.bet_0.67 = 0.30;
            strategy.check = 0.30; // Check to induce
        }
        // Very strong - bet for value
        else if (handCategory === 'veryStrong') {
            strategy.bet_0.67 = 0.40;
            strategy.bet_1.0 = 0.35;
            strategy.bet_0.5 = 0.15;
            strategy.check = 0.10;
        }
        // Strong - bet medium
        else if (handCategory === 'strong') {
            strategy.bet_0.5 = 0.40;
            strategy.bet_0.67 = 0.30;
            strategy.check = 0.25;
            strategy.bet_0.33 = 0.05;
        }
        // Medium-strong - mix of small bets and checks
        else if (handCategory === 'mediumStrong') {
            strategy.bet_0.33 = 0.35;
            strategy.bet_0.5 = 0.25;
            strategy.check = 0.40;
        }
        // Medium hands - check or small bet
        else if (handCategory === 'medium') {
            if (isHeroIP) {
                strategy.check = 0.50;
                strategy.bet_0.33 = 0.35;
                strategy.bet_0.5 = 0.15;
            } else {
                strategy.check = 0.70;
                strategy.bet_0.33 = 0.20;
                strategy.bet_0.5 = 0.10;
            }
        }
        // Draws - semi-bluff or check
        else if (draws.strongDraw) {
            if (isHeroIP) {
                strategy.bet_0.5 = 0.35;
                strategy.bet_0.67 = 0.20;
                strategy.check = 0.45;
            } else {
                strategy.check = 0.60;
                strategy.bet_0.33 = 0.25;
                strategy.bet_0.5 = 0.15;
            }
        }
        // Weak hands - mostly check, occasional bluffs on good boards
        else {
            if (boardTexture.wetness > 0.65 && isHeroIP) {
                strategy.check = 0.60;
                strategy.bet_0.67 = 0.20;
                strategy.bet_0.5 = 0.15;
                strategy.bet_1.0 = 0.05;
            } else {
                strategy.check = 0.85;
                strategy.bet_0.5 = 0.10;
                strategy.bet_0.33 = 0.05;
            }
        }
        
        return strategy;
    }

    // Advanced open action strategy (c-betting)
    getAdvancedOpenActionStrategy(metrics, pot, stack, isHeroIP, street, villainPosition, rangeAdvantage) {
        const { equity, handCategory, draws, boardTexture } = metrics;
        const strategy = {
            check: 0, bet_0.33: 0, bet_0.5: 0, bet_0.67: 0, bet_1.0: 0
        };
        
        // Get target c-bet frequency based on position and board
        const cBetFreq = isHeroIP ? 
            this.config.cBetFrequencies.IP[boardTexture.type] :
            this.config.cBetFrequencies.OOP[boardTexture.type];
        
        // Very strong hands - almost always bet
        if (handCategory === 'veryStrong' || handCategory === 'nuts') {
            strategy.bet_0.67 = 0.40;
            strategy.bet_1.0 = 0.35;
            strategy.bet_0.5 = 0.20;
            strategy.check = 0.05;
        }
        // Strong hands - bet frequently
        else if (handCategory === 'strong') {
            strategy.bet_0.67 = 0.45;
            strategy.bet_0.5 = 0.35;
            strategy.check = 0.15;
            strategy.bet_0.33 = 0.05;
        }
        // Medium-strong - bet or check
        else if (handCategory === 'mediumStrong') {
            strategy.bet_0.5 = 0.40;
            strategy.bet_0.33 = 0.25;
            strategy.check = 0.30;
            strategy.bet_0.67 = 0.05;
        }
        // Medium hands - conditional betting
        else if (handCategory === 'medium') {
            if (boardTexture.wetness < 0.5 || isHeroIP) {
                strategy.bet_0.33 = 0.35;
                strategy.bet_0.5 = 0.20;
                strategy.check = 0.45;
            } else {
                strategy.check = 0.65;
                strategy.bet_0.33 = 0.25;
                strategy.bet_0.5 = 0.10;
            }
        }
        // Draws - semi-bluff
        else if (draws.strongDraw) {
            strategy.bet_0.5 = 0.35;
            strategy.bet_0.67 = 0.25;
            strategy.check = 0.40;
        }
        // Weak hands - bluff to maintain c-bet frequency
        else {
            // Calculate how often we should bluff
            const shouldBluff = Math.random() < (cBetFreq - 0.45);
            
            if (shouldBluff && (boardTexture.wetness > 0.6 || rangeAdvantage.value > 0)) {
                strategy.bet_0.67 = 0.25;
                strategy.bet_0.5 = 0.20;
                strategy.check = 0.55;
            } else {
                strategy.check = 0.80;
                strategy.bet_0.5 = 0.12;
                strategy.bet_0.33 = 0.08;
            }
        }
        
        return strategy;
    }

    // Normalize strategy frequencies
    normalizeStrategy(strategy) {
        const total = Object.values(strategy).reduce((a, b) => a + b, 0);
        if (total === 0 || total === 1) return strategy;
        
        const normalized = {};
        for (let action in strategy) {
            normalized[action] = strategy[action] / total;
        }
        return normalized;
    }

    // Evaluate action with much more sophisticated EV loss calculation
    evaluateAction(playerAction, gtoStrategy, metrics) {
        const playerFreq = gtoStrategy[playerAction] || 0;
        const sortedActions = Object.entries(gtoStrategy)
            .sort((a, b) => b[1] - a[1]);
        
        const optimalAction = sortedActions[0][0];
        const optimalFreq = sortedActions[0][1];
        
        // More accurate EV loss calculation
        let evLoss = 0;
        let category = '';
        
        // Best move: within 3% of optimal OR frequency > 25%
        if (playerFreq >= optimalFreq - 0.03 || playerFreq >= 0.25) {
            category = 'best';
            evLoss = Math.max(0, (optimalFreq - playerFreq) * 0.05);
        }
        // Correct move: frequency between 15-25%
        else if (playerFreq >= 0.15) {
            category = 'correct';
            evLoss = (optimalFreq - playerFreq) * 0.15;
        }
        // Inaccuracy: frequency 8-15%
        else if (playerFreq >= 0.08) {
            category = 'inaccuracy';
            evLoss = 0.3 + (optimalFreq - playerFreq) * 0.2;
        }
        // Wrong: frequency 3-8%
        else if (playerFreq >= 0.03) {
            category = 'wrong';
            evLoss = 0.6 + (optimalFreq - playerFreq) * 0.3;
        }
        // Blunder: frequency < 3%
        else {
            category = 'blunder';
            evLoss = 1.2 + (optimalFreq - playerFreq) * 0.4;
        }
        
        return {
            category,
            evLoss: Math.min(evLoss, 2.5), // Cap at 2.5bb
            playerFrequency: playerFreq,
            optimalAction,
            optimalFrequency: optimalFreq,
            allFrequencies: gtoStrategy,
            top3Actions: sortedActions.slice(0, 3)
        };
    }

    // Helper methods from basic solver
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

    convertButtonAction(buttonAction, buttonSize) {
        if (buttonAction === 'fold') return 'fold';
        if (buttonAction === 'call') return 'call';
        if (buttonAction === 'check') return 'check';
        if (buttonAction === 'raise' || buttonAction === 'bet') {
            return `${buttonAction}_${buttonSize}`;
        }
        return buttonAction;
    }
}

// Replace old solver with advanced solver
// Use window to ensure it's globally accessible
try {
    window.AdvancedGTOSolver = AdvancedGTOSolver;
    window.gtoSolver = new AdvancedGTOSolver();
    var gtoSolver = window.gtoSolver;
    console.log('Advanced GTO Solver loaded successfully');
} catch (error) {
    console.error('Error loading Advanced GTO Solver:', error);
    throw error;
}

