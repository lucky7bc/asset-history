# Sleeper League Trade & Pick History

A lightweight, self-updating web tool that tracks the complete lineage of draft picks and players across trades in your Sleeper fantasy football league. Ever wonder where a 3rd-round pick from three years ago ended up? This tool maps out the entire history—where the asset started, where it traveled, and what player it ultimately turned into.

## Features

- **Full Asset Lineage:** Follow traded picks into the exact players they became, with interactive links and clean trade cards.
- **Automated Data Updates:** Powered by a GitHub Action that crawls the Sleeper API every 3 hours to capture new trades automatically.
- **PWA (Progressive Web App) Ready:** Installable directly to your phone's home screen for a native app-like experience (fast loading, offline caching, and full-screen UI).

---

## Setup & Deployment Guide

To host this tool for free using GitHub Pages and GitHub Actions, follow these steps:

### 1. Create the GitHub Repository
1. Create a new repository on GitHub (e.g., `sleeper-league-history`).
2. Push your project files to the `main` branch. Ensure `crawl.py`, the `site/` folder, and `.github/workflows/update.yml` sit at the root level.

### 2. Configure GitHub Pages
1. Go to your repository on GitHub and click **Settings**.
2. In the left sidebar, click **Pages**.
3. Under **Build and deployment**, change the Source dropdown to **GitHub Actions**.

### 3. Add Your Sleeper League ID
1. Still in repository **Settings**, navigate to **Secrets and variables** > **Actions**.
2. Click on the **Variables** tab (not Secrets).
3. Click **New repository variable**:
   - **Name:** `LEAGUE_ID`
   - **Value:** *Your actual Sleeper league ID for the current season*

### 4. Trigger the First Deploy
1. Click on the **Actions** tab at the top of your repository.
2. Select the **Update data and deploy** workflow on the left.
3. Click **Run workflow** > **Run workflow**. 
4. Once the action completes, your live site URL will be displayed in the deployment step logs!

---

## Installing as a Mobile App (PWA)

Share the GitHub Pages link with your league mates so they can install it directly to their devices:

- **iPhone / iOS:** Open the link in **Safari**, tap the **Share** button, and select **"Add to Home Screen"**.
- **Android:** Open the link in **Chrome**, open the browser menu, and tap **"Install app"** or **"Add to Home Screen"**.
- **Desktop (Chrome/Edge):** Click the install icon in the right side of the address bar.
