# Deployment Guide

## Quick Deploy Options

### 1. GitHub Pages (Recommended - Free & Easy)

**Step-by-step**:

1. Create a new GitHub repository
   - Go to https://github.com/new
   - Name it something like `gto-poker-trainer`
   - Make it public
   - Don't initialize with README

2. Upload files:
   ```bash
   cd /path/to/poker-trainer
   git init
   git add .
   git commit -m "Initial commit - GTO Poker Trainer"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/gto-poker-trainer.git
   git push -u origin main
   ```

3. Enable GitHub Pages:
   - Go to repository Settings
   - Scroll to "Pages" section
   - Source: Select "main" branch
   - Click Save
   - Wait 2-3 minutes

4. Access your site:
   - URL will be: `https://YOUR_USERNAME.github.io/gto-poker-trainer`

### 2. Netlify (Free, Instant)

**Method A: Drag & Drop**
1. Go to https://app.netlify.com/drop
2. Drag the entire `poker-trainer` folder
3. Get instant URL: `https://random-name.netlify.app`

**Method B: Git Integration**
1. Push to GitHub (see above)
2. Go to https://app.netlify.com
3. Click "New site from Git"
4. Connect your repository
5. Deploy settings:
   - Build command: (leave empty)
   - Publish directory: (leave empty or `.`)
6. Click Deploy

### 3. Vercel (Free, Fast)

1. Install Vercel CLI (optional):
   ```bash
   npm install -g vercel
   ```

2. Deploy:
   ```bash
   cd poker-trainer
   vercel
   ```

3. Or use web interface:
   - Go to https://vercel.com/new
   - Import your GitHub repository
   - Click Deploy

### 4. Local Server (Development)

**Python** (pre-installed on Mac/Linux):
```bash
cd poker-trainer
python3 -m http.server 8000
# Visit: http://localhost:8000
```

**Node.js**:
```bash
cd poker-trainer
npx serve
# Visit: http://localhost:3000
```

**PHP**:
```bash
cd poker-trainer
php -S localhost:8000
# Visit: http://localhost:8000
```

### 5. Traditional Web Hosting

Upload files via FTP/SFTP to any web host:
- Bluehost
- HostGator
- SiteGround
- Any shared hosting with HTML support

Just upload all files to your `public_html` or `www` directory.

## Custom Domain (Optional)

### GitHub Pages with Custom Domain

1. Buy domain (Namecheap, Google Domains, etc.)
2. Add CNAME record pointing to: `YOUR_USERNAME.github.io`
3. In GitHub repo, go to Settings → Pages
4. Enter custom domain
5. Enable "Enforce HTTPS"

### Netlify with Custom Domain

1. In Netlify dashboard, go to Domain Settings
2. Add custom domain
3. Follow DNS configuration instructions
4. Netlify provides free SSL automatically

## Testing Before Deployment

1. **Open Locally**:
   ```bash
   cd poker-trainer
   open index.html  # Mac
   start index.html # Windows
   xdg-open index.html # Linux
   ```

2. **Check Console**:
   - Open browser DevTools (F12)
   - Check for JavaScript errors
   - Test all features:
     - Click "START TRAINING"
     - Play a few hands
     - Check statistics update
     - Verify feedback appears

3. **Test Different Browsers**:
   - Chrome ✓
   - Firefox ✓
   - Safari ✓
   - Edge ✓

## Troubleshooting

### Files Not Loading

**Symptom**: Blank page or "Cannot find file" errors

**Solutions**:
1. Check all files are in same directory
2. Verify file names match exactly (case-sensitive)
3. Check browser console for specific errors
4. Ensure no files are blocked by antivirus

### JavaScript Errors

**Symptom**: Buttons don't work, no game starts

**Solutions**:
1. Open browser console (F12)
2. Look for red error messages
3. Verify all `.js` files loaded successfully
4. Check if browser has JavaScript enabled
5. Try different browser

### GitHub Pages Not Working

**Symptom**: 404 error after deployment

**Solutions**:
1. Wait 5-10 minutes (deployment takes time)
2. Verify Pages is enabled in Settings
3. Check branch is set to `main`
4. Ensure index.html is in root directory
5. Check repository is public (or have Pro account)

### Cards/Styles Not Showing

**Symptom**: Content loads but looks broken

**Solutions**:
1. Verify `styles.css` is in same directory
2. Check browser console for CSS load errors
3. Try hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
4. Clear browser cache

## Performance Optimization

### For Production Deployment

1. **Minify Files** (optional):
   ```bash
   # Install minification tools
   npm install -g uglify-js clean-css-cli html-minifier
   
   # Minify
   uglifyjs app.js -o app.min.js
   uglifyjs poker-engine.js -o poker-engine.min.js
   uglifyjs preflop-ranges.js -o preflop-ranges.min.js
   uglifyjs gto-solver.js -o gto-solver.min.js
   cleancss styles.css -o styles.min.css
   
   # Update index.html to reference .min.js files
   ```

2. **Enable Compression**:
   - GitHub Pages: Automatic
   - Netlify: Automatic
   - Vercel: Automatic
   - Traditional hosting: Enable gzip in .htaccess

3. **CDN** (optional):
   - Cloudflare (free): https://www.cloudflare.com/
   - Enables caching and faster global delivery

## Security Considerations

**This is a client-side only app** - No backend, no data storage, no security concerns!

- No user data collected
- No cookies set
- No external API calls
- All processing happens in browser
- Safe to use on any device
- No privacy concerns

## Sharing Your Deployment

Once deployed, share with:
- Poker friends
- Study groups
- Online forums
- Social media
- Poker communities

Example share text:
```
🃏 Free GTO Poker Trainer
Practice your poker skills with realistic scenarios and instant GTO feedback.

✓ No subscription required
✓ Unlimited hands
✓ Detailed statistics
✓ Professional-grade training

Try it: [YOUR_URL_HERE]
```

## Updating Your Deployment

### GitHub Pages

```bash
cd poker-trainer
git add .
git commit -m "Update feature X"
git push
# Wait 2-3 minutes for deployment
```

### Netlify/Vercel with Git

Just push to GitHub - auto-deploys!

### Manual Upload

Re-upload changed files via FTP or drag-and-drop.

## Mobile Considerations

The trainer works on mobile browsers but is optimized for desktop:
- Touch controls work
- Smaller screen may make buttons harder to tap
- Best experience on tablet or larger

For mobile-specific deployment:
- Consider adding viewport meta tag (already included)
- Test on actual devices
- May want larger buttons for better touch targets

## Monitoring & Analytics (Optional)

Add Google Analytics to track usage:

1. Get tracking code from https://analytics.google.com
2. Add to `index.html` before `</head>`:
   ```html
   <!-- Global site tag (gtag.js) - Google Analytics -->
   <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
   <script>
     window.dataLayer = window.dataLayer || [];
     function gtag(){dataLayer.push(arguments);}
     gtag('js', new Date());
     gtag('config', 'G-XXXXXXXXXX');
   </script>
   ```

## Cost Analysis

**GitHub Pages**: $0 (unlimited)
**Netlify Free**: $0 (100GB bandwidth/month - plenty!)
**Vercel Free**: $0 (100GB bandwidth/month)
**Traditional Hosting**: $3-10/month

**Recommendation**: Use GitHub Pages or Netlify for free, unlimited hosting.

---

**You're all set! Deploy and start training! 🚀**

