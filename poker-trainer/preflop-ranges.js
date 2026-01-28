// Preflop Ranges for 6-max Cash Games (NL500 General)

class PreflopRanges {
    constructor() {
        // Single Raised Pot (SRP) Opening Ranges by position
        this.openingRanges = {
            'UTG': [
                // Pairs
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55',
                // Suited Broadway
                'AKs', 'AQs', 'AJs', 'ATs', 'KQs', 'KJs', 'KTs', 'QJs', 'QTs', 'JTs',
                // Suited connectors and gappers
                'T9s', '98s', '87s', '76s', '65s',
                // Suited Ax
                'A9s', 'A8s', 'A5s', 'A4s', 'A3s', 'A2s',
                // Offsuit Broadway
                'AKo', 'AQo', 'AJo', 'KQo'
            ],
            'HJ': [
                // Pairs
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                // Suited Broadway
                'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'QJs', 'QTs', 'Q9s', 'JTs', 'J9s', 'T9s', 'T8s',
                // Suited connectors
                '98s', '87s', '76s', '65s', '54s',
                // Offsuit
                'AKo', 'AQo', 'AJo', 'ATo', 'KQo', 'KJo', 'QJo'
            ],
            'CO': [
                // Pairs (all)
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                // All suited Ax
                'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                // Suited Broadway and connectors
                'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s', 'K4s', 'K3s', 'K2s',
                'QJs', 'QTs', 'Q9s', 'Q8s', 'JTs', 'J9s', 'J8s', 'T9s', 'T8s', 'T7s',
                '98s', '97s', '87s', '86s', '76s', '75s', '65s', '64s', '54s', '53s',
                // Offsuit
                'AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'KQo', 'KJo', 'KTo', 'QJo', 'QTo', 'JTo'
            ],
            'BTN': [
                // Pairs (all)
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                // Suited hands (very wide)
                'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s', 'K4s', 'K3s', 'K2s',
                'QJs', 'QTs', 'Q9s', 'Q8s', 'Q7s', 'Q6s', 'Q5s', 'Q4s', 'Q3s', 'Q2s',
                'JTs', 'J9s', 'J8s', 'J7s', 'J6s', 'T9s', 'T8s', 'T7s', 'T6s',
                '98s', '97s', '96s', '87s', '86s', '85s', '76s', '75s', '74s', '65s', '64s', '54s', '53s',
                // Offsuit Broadway
                'AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'A8o', 'A7o', 'A6o', 'A5o',
                'KQo', 'KJo', 'KTo', 'K9o', 'QJo', 'QTo', 'Q9o', 'JTo', 'J9o', 'T9o', 'T8o', '98o'
            ],
            'SB': [
                // Pairs (all)
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                // Suited (very wide vs BB)
                'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s', 'K4s', 'K3s', 'K2s',
                'QJs', 'QTs', 'Q9s', 'Q8s', 'Q7s', 'Q6s', 'Q5s', 'Q4s',
                'JTs', 'J9s', 'J8s', 'J7s', 'T9s', 'T8s', 'T7s', '98s', '97s', '87s', '86s', '76s', '75s', '65s', '54s',
                // Offsuit
                'AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'A8o', 'A7o', 'A6o', 'A5o', 'A4o',
                'KQo', 'KJo', 'KTo', 'K9o', 'K8o', 'QJo', 'QTo', 'Q9o', 'JTo', 'J9o', 'T9o', 'T8o', '98o', '87o'
            ]
        };

        // Calling ranges vs open (IP - In Position)
        this.callingRangesIP = {
            'HJ_vs_UTG': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'QJs', 'QTs', 'JTs', 'T9s', '98s', '87s', '76s', '65s', '54s',
                'AJo', 'ATo', 'KQo'
            ],
            'CO_vs_UTG': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'QJs', 'QTs', 'Q9s', 'JTs', 'J9s', 'T9s', 'T8s',
                '98s', '87s', '76s', '65s', '54s',
                'AJo', 'ATo', 'KQo', 'KJo'
            ],
            'CO_vs_HJ': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'QJs', 'QTs', 'Q9s', 'JTs', 'J9s', 'T9s', 'T8s',
                '98s', '87s', '76s', '65s', '54s', '53s',
                'AJo', 'ATo', 'A9o', 'KQo', 'KJo', 'QJo'
            ],
            'BTN_vs_UTG': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'QJs', 'QTs', 'Q9s', 'JTs', 'J9s', 'T9s', 'T8s', 'T7s',
                '98s', '97s', '87s', '86s', '76s', '75s', '65s', '64s', '54s', '53s',
                'AJo', 'ATo', 'A9o', 'KQo', 'KJo', 'QJo'
            ],
            'BTN_vs_HJ': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'QJs', 'QTs', 'Q9s', 'Q8s', 'JTs', 'J9s', 'J8s',
                'T9s', 'T8s', 'T7s', '98s', '97s', '87s', '86s', '76s', '75s', '65s', '64s', '54s', '53s',
                'AJo', 'ATo', 'A9o', 'A8o', 'KQo', 'KJo', 'KTo', 'QJo', 'QTo', 'JTo'
            ],
            'BTN_vs_CO': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'QJs', 'QTs', 'Q9s', 'Q8s', 'Q7s',
                'JTs', 'J9s', 'J8s', 'J7s', 'T9s', 'T8s', 'T7s', '98s', '97s', '96s', '87s', '86s', '76s', '75s', '65s', '64s', '54s', '53s',
                'AJo', 'ATo', 'A9o', 'A8o', 'A7o', 'KQo', 'KJo', 'KTo', 'K9o', 'QJo', 'QTo', 'Q9o', 'JTo', 'J9o', 'T9o'
            ]
        };

        // Calling ranges OOP (Out of Position)
        this.callingRangesOOP = {
            'BB_vs_UTG': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'QJs', 'QTs', 'Q9s', 'JTs', 'J9s', 'T9s', 'T8s',
                '98s', '87s', '76s', '65s', '54s',
                'AJo', 'ATo', 'KQo'
            ],
            'BB_vs_HJ': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'QJs', 'QTs', 'Q9s', 'Q8s', 'JTs', 'J9s', 'J8s',
                'T9s', 'T8s', 'T7s', '98s', '97s', '87s', '86s', '76s', '75s', '65s', '64s', '54s',
                'AJo', 'ATo', 'A9o', 'KQo', 'KJo', 'QJo'
            ],
            'BB_vs_CO': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'QJs', 'QTs', 'Q9s', 'Q8s', 'Q7s',
                'JTs', 'J9s', 'J8s', 'J7s', 'T9s', 'T8s', 'T7s', '98s', '97s', '87s', '86s', '76s', '75s', '65s', '64s', '54s', '53s',
                'AJo', 'ATo', 'A9o', 'A8o', 'KQo', 'KJo', 'KTo', 'QJo', 'QTo', 'JTo'
            ],
            'BB_vs_BTN': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s', 'K4s', 'K3s', 'K2s',
                'QJs', 'QTs', 'Q9s', 'Q8s', 'Q7s', 'Q6s', 'Q5s', 'JTs', 'J9s', 'J8s', 'J7s', 'J6s',
                'T9s', 'T8s', 'T7s', 'T6s', '98s', '97s', '96s', '87s', '86s', '85s', '76s', '75s', '74s', '65s', '64s', '54s', '53s', '43s',
                'AJo', 'ATo', 'A9o', 'A8o', 'A7o', 'A6o', 'A5o', 'A4o',
                'KQo', 'KJo', 'KTo', 'K9o', 'K8o', 'QJo', 'QTo', 'Q9o', 'JTo', 'J9o', 'T9o', 'T8o', '98o', '87o', '76o'
            ],
            'BB_vs_SB': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22',
                'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'K7s', 'K6s', 'K5s', 'K4s', 'K3s', 'K2s',
                'QJs', 'QTs', 'Q9s', 'Q8s', 'Q7s', 'Q6s', 'Q5s', 'Q4s', 'Q3s', 'Q2s',
                'JTs', 'J9s', 'J8s', 'J7s', 'J6s', 'J5s', 'T9s', 'T8s', 'T7s', 'T6s', 'T5s',
                '98s', '97s', '96s', '95s', '87s', '86s', '85s', '76s', '75s', '74s', '65s', '64s', '63s', '54s', '53s', '52s', '43s', '42s', '32s',
                'AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'A8o', 'A7o', 'A6o', 'A5o', 'A4o', 'A3o', 'A2o',
                'KQo', 'KJo', 'KTo', 'K9o', 'K8o', 'K7o', 'K6o', 'QJo', 'QTo', 'Q9o', 'Q8o', 'JTo', 'J9o', 'J8o', 'T9o', 'T8o', '98o', '87o', '76o', '65o'
            ]
        };

        // 3-bet ranges (comprehensive)
        this.threeBetRanges = {
            'BB_vs_BTN': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77',
                'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'QJs', 'QTs', 'JTs', 'J9s', 'T9s', '98s', '87s', '76s',
                'AKo', 'AQo', 'AJo', 'ATo', 'KQo'
            ],
            'BB_vs_SB': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55',
                'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'K8s', 'QJs', 'QTs', 'Q9s', 'JTs', 'J9s', 'T9s', 'T8s', '98s', '87s', '76s', '65s',
                'AKo', 'AQo', 'AJo', 'ATo', 'A9o', 'KQo', 'KJo'
            ],
            'BB_vs_CO': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88',
                'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'QJs', 'JTs',
                'AKo', 'AQo', 'AJo', 'KQo'
            ],
            'BB_vs_HJ': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99',
                'AKs', 'AQs', 'AJs', 'ATs', 'A5s', 'A4s',
                'KQs', 'KJs', 'QJs',
                'AKo', 'AQo', 'AJo'
            ],
            'BB_vs_UTG': [
                'AA', 'KK', 'QQ', 'JJ', 'TT',
                'AKs', 'AQs', 'AJs', 'A5s', 'A4s',
                'KQs', 'QJs',
                'AKo', 'AQo'
            ],
            'SB_vs_BTN': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88',
                'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'QJs', 'JTs',
                'AKo', 'AQo', 'AJo', 'KQo'
            ],
            'SB_vs_CO': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99',
                'AKs', 'AQs', 'AJs', 'ATs', 'A5s', 'A4s',
                'KQs', 'KJs', 'QJs',
                'AKo', 'AQo', 'AJo'
            ],
            'BTN_vs_CO': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66',
                'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A8s', 'A7s', 'A6s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'K9s', 'QJs', 'QTs', 'JTs', 'J9s', 'T9s', '98s', '87s', '76s', '65s',
                'AKo', 'AQo', 'AJo', 'ATo', 'KQo', 'KJo'
            ],
            'BTN_vs_HJ': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77',
                'AKs', 'AQs', 'AJs', 'ATs', 'A9s', 'A5s', 'A4s', 'A3s', 'A2s',
                'KQs', 'KJs', 'KTs', 'QJs', 'JTs', 'T9s',
                'AKo', 'AQo', 'AJo', 'KQo'
            ],
            'BTN_vs_UTG': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99',
                'AKs', 'AQs', 'AJs', 'A5s', 'A4s',
                'KQs', 'KJs', 'QJs',
                'AKo', 'AQo'
            ],
            'CO_vs_HJ': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88',
                'AKs', 'AQs', 'AJs', 'ATs', 'A5s', 'A4s', 'A3s',
                'KQs', 'KJs', 'QJs', 'JTs',
                'AKo', 'AQo', 'AJo'
            ],
            'CO_vs_UTG': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99',
                'AKs', 'AQs', 'AJs', 'A5s', 'A4s',
                'KQs', 'QJs',
                'AKo', 'AQo'
            ],
            'HJ_vs_UTG': [
                'AA', 'KK', 'QQ', 'JJ', 'TT',
                'AKs', 'AQs', 'AJs', 'A5s',
                'KQs', 'QJs',
                'AKo', 'AQo'
            ]
        };
        
        // Squeezing ranges (vs open and call)
        this.squeezeRanges = {
            'BB_squeeze': [
                'AA', 'KK', 'QQ', 'JJ', 'TT',
                'AKs', 'AQs', 'AJs', 'A5s', 'A4s',
                'KQs', 'QJs',
                'AKo', 'AQo'
            ],
            'SB_squeeze': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', '99',
                'AKs', 'AQs', 'AJs', 'ATs', 'A5s', 'A4s',
                'KQs', 'KJs', 'QJs',
                'AKo', 'AQo', 'AJo'
            ]
        };
        
        // 4-bet ranges
        this.fourBetRanges = {
            'polarized': [
                'AA', 'KK', 'QQ', 'AKs', 'A5s', 'A4s', 'AKo'
            ],
            'linear': [
                'AA', 'KK', 'QQ', 'JJ', 'TT', 'AKs', 'AQs', 'AKo'
            ],
            'tight': [
                'AA', 'KK', 'AKs', 'AKo'
            ]
        };
    }

    // Check if hand is in range
    isHandInRange(hand, range) {
        const category = this.getHandCategory(hand);
        return range.includes(category);
    }

    // Get hand category (AA, AKs, AKo, etc.)
    getHandCategory(cards) {
        const ranks = cards.map(c => c.rank).sort((a, b) => {
            const valA = '23456789TJQKA'.indexOf(a);
            const valB = '23456789TJQKA'.indexOf(b);
            return valB - valA;
        });
        const suited = cards[0].suit === cards[1].suit;
        
        if (ranks[0] === ranks[1]) {
            return `${ranks[0]}${ranks[0]}`;
        }
        
        return suited ? `${ranks[0]}${ranks[1]}s` : `${ranks[0]}${ranks[1]}o`;
    }

    // Get appropriate range based on scenario
    getRange(position, action, vsPosition = null) {
        if (action === 'open') {
            return this.openingRanges[position] || [];
        }
        
        if (action === 'call' && vsPosition) {
            const key = `${position}_vs_${vsPosition}`;
            return this.callingRangesIP[key] || this.callingRangesOOP[key] || [];
        }
        
        if (action === '3bet' && vsPosition) {
            const key = `${position}_vs_${vsPosition}`;
            return this.threeBetRanges[key] || [];
        }
        
        return [];
    }

    // Generate random hand from range
    getRandomHandFromRange(range, excludeCards = []) {
        const availableHands = range.filter(category => {
            const hands = this.getCategoryHands(category);
            return hands.some(hand => 
                !hand.some(card => 
                    excludeCards.some(excluded => 
                        excluded.rank === card.rank && excluded.suit === card.suit
                    )
                )
            );
        });
        
        if (availableHands.length === 0) return null;
        
        const randomCategory = availableHands[Math.floor(Math.random() * availableHands.length)];
        const hands = this.getCategoryHands(randomCategory);
        const validHands = hands.filter(hand => 
            !hand.some(card => 
                excludeCards.some(excluded => 
                    excluded.rank === card.rank && excluded.suit === card.suit
                )
            )
        );
        
        if (validHands.length === 0) return null;
        return validHands[Math.floor(Math.random() * validHands.length)];
    }

    // Get all possible hands for a category
    getCategoryHands(category) {
        const suits = ['♠', '♥', '♦', '♣'];
        const hands = [];
        
        if (category.length === 2) {
            // Pocket pair
            const rank = category[0];
            for (let i = 0; i < suits.length; i++) {
                for (let j = i + 1; j < suits.length; j++) {
                    hands.push([
                        { rank, suit: suits[i] },
                        { rank, suit: suits[j] }
                    ]);
                }
            }
        } else {
            const rank1 = category[0];
            const rank2 = category[1];
            const suited = category[2] === 's';
            
            if (suited) {
                for (let suit of suits) {
                    hands.push([
                        { rank: rank1, suit },
                        { rank: rank2, suit }
                    ]);
                }
            } else {
                for (let suit1 of suits) {
                    for (let suit2 of suits) {
                        if (suit1 !== suit2) {
                            hands.push([
                                { rank: rank1, suit: suit1 },
                                { rank: rank2, suit: suit2 }
                            ]);
                        }
                    }
                }
            }
        }
        
        return hands;
    }

    // Get all possible hands from a range
    getAllHandsFromRange(range) {
        const allHands = [];
        for (let category of range) {
            allHands.push(...this.getCategoryHands(category));
        }
        return allHands;
    }
}

const preflopRanges = new PreflopRanges();

