// Poker Engine - Hand Evaluation and Core Logic

class PokerEngine {
    constructor() {
        this.suits = ['♠', '♥', '♦', '♣'];
        this.ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
        this.rankValues = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, 
            '9': 9, 'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
        };
        this.suitSymbols = {
            'spades': '♠',
            'hearts': '♥',
            'diamonds': '♦',
            'clubs': '♣'
        };
    }

    createDeck() {
        const deck = [];
        for (let suit of this.suits) {
            for (let rank of this.ranks) {
                deck.push({ rank, suit });
            }
        }
        return deck;
    }

    shuffle(deck) {
        const shuffled = [...deck];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
    }

    cardToString(card) {
        return `${card.rank}${card.suit}`;
    }

    stringToCard(str) {
        return {
            rank: str[0],
            suit: str[1]
        };
    }

    // Evaluate hand strength (returns 0-9, higher is better)
    evaluateHand(cards) {
        if (cards.length < 5) return { rank: 0, value: 0, description: 'High Card' };

        const allCombos = this.getCombinations(cards, 5);
        let bestHand = { rank: 0, value: 0, description: 'High Card', kickers: [] };

        for (let combo of allCombos) {
            const evaluation = this.evaluateFiveCards(combo);
            if (evaluation.rank > bestHand.rank || 
                (evaluation.rank === bestHand.rank && evaluation.value > bestHand.value)) {
                bestHand = evaluation;
            }
        }

        return bestHand;
    }

    evaluateFiveCards(cards) {
        const ranks = cards.map(c => this.rankValues[c.rank]);
        const suits = cards.map(c => c.suit);
        const rankCounts = {};
        
        ranks.forEach(r => rankCounts[r] = (rankCounts[r] || 0) + 1);
        const counts = Object.values(rankCounts).sort((a, b) => b - a);
        const uniqueRanks = Object.keys(rankCounts).map(Number).sort((a, b) => b - a);
        
        const isFlush = suits.every(s => s === suits[0]);
        const sortedRanks = [...ranks].sort((a, b) => b - a);
        const isStraight = this.checkStraight(sortedRanks);
        
        // Straight Flush
        if (isFlush && isStraight) {
            return {
                rank: 8,
                value: Math.max(...sortedRanks),
                description: sortedRanks[0] === 14 ? 'Royal Flush' : 'Straight Flush',
                kickers: sortedRanks
            };
        }
        
        // Four of a Kind
        if (counts[0] === 4) {
            const quad = uniqueRanks.find(r => rankCounts[r] === 4);
            const kicker = uniqueRanks.find(r => rankCounts[r] === 1);
            return {
                rank: 7,
                value: quad * 1000 + kicker,
                description: 'Four of a Kind',
                kickers: [quad, kicker]
            };
        }
        
        // Full House
        if (counts[0] === 3 && counts[1] === 2) {
            const trips = uniqueRanks.find(r => rankCounts[r] === 3);
            const pair = uniqueRanks.find(r => rankCounts[r] === 2);
            return {
                rank: 6,
                value: trips * 1000 + pair,
                description: 'Full House',
                kickers: [trips, pair]
            };
        }
        
        // Flush
        if (isFlush) {
            return {
                rank: 5,
                value: sortedRanks.reduce((acc, r, i) => acc + r * Math.pow(100, 4 - i), 0),
                description: 'Flush',
                kickers: sortedRanks
            };
        }
        
        // Straight
        if (isStraight) {
            return {
                rank: 4,
                value: Math.max(...sortedRanks),
                description: 'Straight',
                kickers: sortedRanks
            };
        }
        
        // Three of a Kind
        if (counts[0] === 3) {
            const trips = uniqueRanks.find(r => rankCounts[r] === 3);
            const kickers = uniqueRanks.filter(r => rankCounts[r] === 1);
            return {
                rank: 3,
                value: trips * 10000 + kickers[0] * 100 + kickers[1],
                description: 'Three of a Kind',
                kickers: [trips, ...kickers]
            };
        }
        
        // Two Pair
        if (counts[0] === 2 && counts[1] === 2) {
            const pairs = uniqueRanks.filter(r => rankCounts[r] === 2).sort((a, b) => b - a);
            const kicker = uniqueRanks.find(r => rankCounts[r] === 1);
            return {
                rank: 2,
                value: pairs[0] * 10000 + pairs[1] * 100 + kicker,
                description: 'Two Pair',
                kickers: [...pairs, kicker]
            };
        }
        
        // One Pair
        if (counts[0] === 2) {
            const pair = uniqueRanks.find(r => rankCounts[r] === 2);
            const kickers = uniqueRanks.filter(r => rankCounts[r] === 1);
            return {
                rank: 1,
                value: pair * 1000000 + kickers.reduce((acc, k, i) => acc + k * Math.pow(100, 2 - i), 0),
                description: 'One Pair',
                kickers: [pair, ...kickers]
            };
        }
        
        // High Card
        return {
            rank: 0,
            value: sortedRanks.reduce((acc, r, i) => acc + r * Math.pow(100, 4 - i), 0),
            description: 'High Card',
            kickers: sortedRanks
        };
    }

    checkStraight(sortedRanks) {
        // Check regular straight
        for (let i = 0; i < sortedRanks.length - 1; i++) {
            if (sortedRanks[i] - sortedRanks[i + 1] !== 1) {
                // Check for wheel (A-2-3-4-5)
                if (sortedRanks[0] === 14 && sortedRanks[1] === 5 && 
                    sortedRanks[2] === 4 && sortedRanks[3] === 3 && sortedRanks[4] === 2) {
                    return true;
                }
                return false;
            }
        }
        return true;
    }

    getCombinations(arr, size) {
        if (size > arr.length) return [];
        if (size === arr.length) return [arr];
        if (size === 1) return arr.map(item => [item]);
        
        const combos = [];
        for (let i = 0; i <= arr.length - size; i++) {
            const head = arr[i];
            const tailCombos = this.getCombinations(arr.slice(i + 1), size - 1);
            for (let tail of tailCombos) {
                combos.push([head, ...tail]);
            }
        }
        return combos;
    }

    // Monte Carlo equity calculation
    calculateEquity(heroCards, board, villainRange, numSimulations = 1000) {
        let wins = 0;
        let ties = 0;

        for (let i = 0; i < numSimulations; i++) {
            let deck = this.createDeck();
            
            // Remove known cards from deck
            const usedCards = [...heroCards, ...board];
            deck = deck.filter(card => !usedCards.some(used => 
                used.rank === card.rank && used.suit === card.suit
            ));
            
            deck = this.shuffle(deck);
            
            // Deal remaining board cards if needed
            const remainingBoardCards = 5 - board.length;
            const fullBoard = [...board, ...deck.slice(0, remainingBoardCards)];
            deck = deck.slice(remainingBoardCards);
            
            // Get random villain hand from range
            const villainHand = [deck[0], deck[1]];
            
            // Evaluate hands
            const heroEval = this.evaluateHand([...heroCards, ...fullBoard]);
            const villainEval = this.evaluateHand([...villainHand, ...fullBoard]);
            
            if (heroEval.rank > villainEval.rank || 
                (heroEval.rank === villainEval.rank && heroEval.value > villainEval.value)) {
                wins++;
            } else if (heroEval.rank === villainEval.rank && heroEval.value === villainEval.value) {
                ties++;
            }
        }

        return (wins + ties * 0.5) / numSimulations;
    }

    // Calculate hand strength (0-1) considering board texture
    calculateHandStrength(heroCards, board) {
        const handEval = this.evaluateHand([...heroCards, ...board]);
        
        // Base strength from hand rank
        let strength = handEval.rank / 8;
        
        // Adjust for card values
        const heroRanks = heroCards.map(c => this.rankValues[c.rank]);
        const avgHeroRank = heroRanks.reduce((a, b) => a + b, 0) / heroRanks.length;
        strength += (avgHeroRank - 7.5) / 100; // Normalize around 7.5
        
        return Math.max(0, Math.min(1, strength));
    }

    // Calculate draw potential
    calculateDrawStrength(heroCards, board) {
        if (board.length >= 5) return 0;
        
        let outs = 0;
        const deck = this.createDeck();
        const usedCards = [...heroCards, ...board];
        const remainingDeck = deck.filter(card => !usedCards.some(used => 
            used.rank === card.rank && used.suit === card.suit
        ));
        
        const currentEval = this.evaluateHand([...heroCards, ...board]);
        
        // Count outs (cards that improve hand)
        for (let card of remainingDeck) {
            const newBoard = [...board, card];
            const newEval = this.evaluateHand([...heroCards, ...newBoard]);
            
            if (newEval.rank > currentEval.rank || 
                (newEval.rank === currentEval.rank && newEval.value > currentEval.value)) {
                outs++;
            }
        }
        
        const totalRemaining = remainingDeck.length;
        return outs / totalRemaining;
    }

    // Analyze board texture
    analyzeBoardTexture(board) {
        if (board.length < 3) return { wetness: 0.5, connected: false, paired: false, flush: false };
        
        const ranks = board.map(c => this.rankValues[c.rank]).sort((a, b) => a - b);
        const suits = board.map(c => c.suit);
        
        // Check for pairs
        const rankCounts = {};
        ranks.forEach(r => rankCounts[r] = (rankCounts[r] || 0) + 1);
        const paired = Object.values(rankCounts).some(count => count >= 2);
        
        // Check for flush draw
        const suitCounts = {};
        suits.forEach(s => suitCounts[s] = (suitCounts[s] || 0) + 1);
        const flushDraw = Object.values(suitCounts).some(count => count >= 3);
        
        // Check connectivity (straight possibilities)
        let maxGap = 0;
        for (let i = 1; i < ranks.length; i++) {
            maxGap = Math.max(maxGap, ranks[i] - ranks[i-1]);
        }
        const connected = maxGap <= 3;
        
        // Calculate wetness (0-1, higher = wetter/more dangerous)
        let wetness = 0.3; // Base
        if (flushDraw) wetness += 0.2;
        if (connected) wetness += 0.2;
        if (paired) wetness += 0.15;
        if (ranks[ranks.length - 1] >= 11) wetness += 0.15; // High cards
        
        return {
            wetness: Math.min(1, wetness),
            connected,
            paired,
            flushDraw,
            highCards: ranks.filter(r => r >= 11).length
        };
    }

    // Parse hand notation (e.g., "AhKd" to card objects)
    parseHand(handStr) {
        const cards = [];
        for (let i = 0; i < handStr.length; i += 2) {
            const rank = handStr[i];
            const suitChar = handStr[i + 1];
            let suit;
            switch(suitChar.toLowerCase()) {
                case 'h': suit = '♥'; break;
                case 'd': suit = '♦'; break;
                case 'c': suit = '♣'; break;
                case 's': suit = '♠'; break;
                default: suit = suitChar;
            }
            cards.push({ rank, suit });
        }
        return cards;
    }

    // Hand comparison for ranges
    compareHands(hand1, hand2) {
        const r1 = Math.max(this.rankValues[hand1[0].rank], this.rankValues[hand1[1].rank]);
        const r2 = Math.min(this.rankValues[hand1[0].rank], this.rankValues[hand1[1].rank]);
        const r3 = Math.max(this.rankValues[hand2[0].rank], this.rankValues[hand2[1].rank]);
        const r4 = Math.min(this.rankValues[hand2[0].rank], this.rankValues[hand2[1].rank]);
        
        if (r1 !== r3) return r3 - r1;
        return r4 - r2;
    }

    // Get hand category for range analysis
    getHandCategory(cards) {
        const ranks = cards.map(c => this.rankValues[c.rank]).sort((a, b) => b - a);
        const suited = cards[0].suit === cards[1].suit;
        
        if (ranks[0] === ranks[1]) {
            return `${cards[0].rank}${cards[0].rank}`; // Pocket pair
        }
        
        const highCard = this.ranks[ranks[0] - 2];
        const lowCard = this.ranks[ranks[1] - 2];
        return suited ? `${highCard}${lowCard}s` : `${highCard}${lowCard}o`;
    }
}

// Export for use in other files
const pokerEngine = new PokerEngine();

