# Using This Workflow in Your Roast Repository

This workflow automatically processes `.alog` files and maintains a roast log.

## Setup Instructions

1. **Copy this workflow file** to your roast repository:
   ```
   .github/workflows/render.yml
   ```

2. **Copy the required scripts** to the root of your roast repository:
   - `alog_renderer.py`
   - `update_roast_log.py`
   - `requirements.txt`

3. **Create a `ROASTS.md` file** in the root of your repository:
   ```markdown
   # Roast Log

   A chronological log of all coffee roasts.

   ```

4. **Ensure GitHub Actions has write permissions**:
   - Go to your repository **Settings** → **Actions** → **General**
   - Under "Workflow permissions", select **Read and write permissions**
   - Save

## How It Works

When you push a new or modified `.alog` file:

1. The workflow detects the change
2. Extracts the batch number from the file
3. Renders the profile to `renders/#<batch>.png`
4. Updates `ROASTS.md` with the roast entry
5. Commits the rendered image and updated log back to your repository

## Result

Your `ROASTS.md` will maintain a table like this:

| Roast | Date | Time | Dev % | Profile |
|-------|------|------|-------|----------|
| #28 | Fri Nov 28 2025 | 10.1 min | 11.3% | ![Profile](renders/#28.png) |
| #27 | Thu Nov 27 2025 | 9.5 min | 12.1% | ![Profile](renders/#27.png) |

Sorted newest first!
