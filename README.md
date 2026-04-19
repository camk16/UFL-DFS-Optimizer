# 🏈 UFL DFS Lineup Optimizer

A free, browser-based DraftKings lineup optimizer for the UFL — built with Streamlit and PuLP.

---

## 📁 Files In This Project

| File | What It Does |
|---|---|
| `app.py` | The visual web app (what you see in the browser) |
| `optimizer.py` | The math engine that builds optimal lineups |
| `requirements.txt` | Tells the server which Python packages to install |

---

## 🚀 Complete Setup Guide (Start Here)

Follow these steps **in order**. Each step links to where you need to go.

---

### STEP 1 — Create a GitHub Account

GitHub is a free website that stores your code. Think of it like Google Drive, but for code files.

1. Go to **https://github.com**
2. Click **"Sign up"** in the top right
3. Enter your email, create a password, and choose a username
4. Verify your email when prompted
5. You're in! ✅

---

### STEP 2 — Create a New Repository (Your Code Folder)

A "repository" (or "repo") is just a folder on GitHub that holds your project files.

1. Once logged into GitHub, click the **"+"** icon in the top right corner
2. Click **"New repository"**
3. Fill in the form:
   - **Repository name:** `ufl-dfs-optimizer` (or any name you like)
   - **Description:** `UFL DFS lineup optimizer` (optional)
   - **Visibility:** Set to **Public** ← important for free Streamlit hosting
   - Leave everything else as default
4. Click **"Create repository"** (green button at the bottom)
5. You'll land on an empty repo page ✅

---

### STEP 3 — Upload Your Files to GitHub

Now we'll put the 3 code files into your new repo.

1. On your repo page, click **"uploading an existing file"** (it's a link in the middle of the page)
   - If you don't see it, click **"Add file"** → **"Upload files"**
2. Drag and drop all 3 files into the upload box:
   - `app.py`
   - `optimizer.py`
   - `requirements.txt`
3. Scroll down and click **"Commit changes"** (green button)
4. Your files are now on GitHub ✅

---

### STEP 4 — Create a Streamlit Account

Streamlit Community Cloud is a free service that turns your GitHub code into a live website.

1. Go to **https://share.streamlit.io**
2. Click **"Sign up"**
3. Choose **"Continue with GitHub"** — this links your Streamlit account to your GitHub automatically
4. Authorize the connection when prompted
5. You're in! ✅

---

### STEP 5 — Deploy Your App

1. On the Streamlit dashboard, click **"New app"** (top right)
2. Fill in the form:
   - **Repository:** Select `ufl-dfs-optimizer` (your GitHub repo from Step 2)
   - **Branch:** `main`
   - **Main file path:** `app.py`
3. Click **"Deploy!"**
4. Wait 1–3 minutes while Streamlit installs your app
5. Your app will open automatically in the browser with a unique URL like:
   `https://yourname-ufl-dfs-optimizer-app-xyz.streamlit.app`
6. Bookmark that URL — it's your optimizer! ✅

---

### STEP 6 — Use Your Optimizer Each Week

1. **Download your projections** from your source (FantasyPros, RotoGrinders, ETR, etc.) as a CSV
2. **Open your Streamlit app URL** in any browser
3. **Upload the CSV** using the sidebar
4. **Configure your constraints** (salary, ownership cap, QB stack, etc.)
5. **Lock or exclude players** as desired
6. **Click "Generate Lineups"**
7. **Download your lineups** and upload to DraftKings

---

## 📋 CSV Format Requirements

Your weekly CSV must have these columns (exact spelling matters):

| Column | Required? | Description |
|---|---|---|
| Name | ✅ Yes | Player's full name |
| Position | ✅ Yes | QB, RB, WR, TE, or DST |
| Team | ✅ Yes | Team abbreviation (e.g. KC, SF) |
| Salary | ✅ Yes | DraftKings salary (e.g. 7500) |
| Ownership | ✅ Yes | Projected ownership % (e.g. 22.5) |
| Projection | Optional | Projected fantasy points |
| ETR.Val | Optional | ETR value metric |
| T.Val | Optional | T value metric |

---

## 🏟️ UFL Roster Format (DraftKings)

| Slot | Eligible Positions |
|---|---|
| QB | QB only |
| RB | RB only |
| WR/TE | WR or TE |
| WR/TE | WR or TE |
| FLEX | RB, WR, or TE |
| FLEX | RB, WR, or TE |
| DST | DST only |

**Salary Cap:** $50,000

---

## ⚙️ Constraints Available

| Constraint | What It Does |
|---|---|
| Optimize By | Choose Projection, ETR.Val, or T.Val as the objective |
| Number of Lineups | Generate 1 to 150 unique lineups |
| Min Salary | Force the optimizer to spend at least X (default $49,000) |
| Max Cumulative Ownership | Cap the sum of all player ownership %s |
| Max Players Per Team | Prevent stacking too many players from one team |
| Force QB Stack | Require QB to be paired with WR/TE from same team |
| Lock Players | Force specific players into all lineups |
| Exclude Players | Remove specific players from all lineups |
| Exposure Limits | Cap how many lineups a specific player appears in |

---

## ❓ FAQ

**Q: My app is sleeping when I open it. What do I do?**
A: Free Streamlit apps "sleep" after inactivity. Just click "Yes, get this app back up!" and wait ~30 seconds.

**Q: I got an error saying a column is missing.**
A: Double-check your CSV has the exact column names: Name, Position, Team, Salary, Ownership. Capitalization matters.

**Q: The optimizer only generated fewer lineups than I asked for.**
A: Your constraints are too tight — there aren't enough valid combinations. Try raising the ownership cap, lowering the min salary, or unlocking players.

**Q: Can I use this for FanDuel too?**
A: Not currently — FanDuel uses different roster slots and salary caps. This can be added in a future update.
