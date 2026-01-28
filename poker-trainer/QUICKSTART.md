# Quick Start Guide

## Running the Trainer

### Easiest Method: Open Locally

1. Navigate to the `poker-trainer` folder
2. Double-click `index.html`
3. Your browser will open the trainer
4. Click "START TRAINING" and begin!

### Using Python Server (Recommended)

```bash
cd poker-trainer
python3 -m http.server 8000
```

Then open: `http://localhost:8000`

### Deploy to GitHub Pages

1. Create a new repository on GitHub
2. Upload all files from the `poker-trainer` folder
3. Go to Settings → Pages → Select main branch → Save
4. Your site will be live at: `https://yourusername.github.io/repo-name`

## How to Play

1. **Settings Screen**
   - Configure your training preferences
   - Currently supports SRP (Single Raised Pot) from the flop
   - Click "START TRAINING"

2. **Playing Hands**
   - You'll see your hole cards at the bottom
   - The flop is shown in the center
   - The pot size and preflop action are displayed
   - Choose your action using the buttons at the bottom

3. **Understanding Feedback**
   - **Green**: Best or Correct move
   - **Yellow**: Inaccuracy (suboptimal but not terrible)
   - **Orange**: Wrong move
   - **Red**: Blunder (serious mistake)

4. **Tracking Progress**
   - Left sidebar shows your statistics
   - **GTO Score**: Overall accuracy (higher is better)
   - **Move Breakdown**: How many of each type
   - **EV Loss**: Big blinds lost due to mistakes
   - **History**: Review recent hands

## Tips for Training

1. **Focus on Patterns**: Notice which boards favor betting vs checking
2. **Position Matters**: You'll be more aggressive in position
3. **Hand Strength**: Consider both made hands and draws
4. **Board Texture**: Wet boards (connected, flush draws) play differently than dry boards
5. **Balance**: GTO involves mixing strategies, so "correct" moves include multiple options

## Understanding Your Score

- **90%+**: Excellent, near-GTO play
- **80-90%**: Very good, minor mistakes
- **70-80%**: Good, some improvement needed
- **60-70%**: Decent, focus on fundamentals
- **Below 60%**: Needs work, review feedback carefully

## Common Mistakes to Avoid

1. **Over-folding**: Not defending enough against bets
2. **Under-bluffing**: Always betting for value, never bluffing
3. **Wrong bet sizing**: Using inappropriate bet sizes for the situation
4. **Ignoring position**: Not adjusting strategy for IP vs OOP
5. **Board texture blindness**: Playing same on all board types

## What Makes This GTO?

The trainer uses:
- Proper preflop ranges (only realistic hands)
- Equity calculations
- Board texture analysis
- Position-adjusted strategies
- Balanced frequencies (value + bluffs)
- Proper bet sizing options
- Minimum defense frequency calculations

While not solver-perfect, it provides excellent GTO approximations for training purposes.

---

Have fun training! 🎯

