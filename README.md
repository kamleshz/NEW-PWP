# PWP Bot Web App

This project converts the original desktop PWP bot into a Flask web app.

## Features

- Portal login
- Excel validation
- Data upload
- Invoice PDF upload
- Delete upload data
- Scrape and export reports
- Background job polling for long Selenium actions
- Render-ready Docker deployment

## Project Files

- `app.py`: Flask routes and background job handling
- `pwp_bot_service.py`: Selenium and Excel processing logic
- `templates/index.html`: Web dashboard
- `Dockerfile`: Production container with Chromium and Chromedriver
- `render.yaml`: Render service definition
- `.env.example`: Deployment environment reference

## Local Run

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python app.py
```

4. Open `http://localhost:5000`

## Desktop Build

Use the desktop bot when users must see and interact with the browser on their own Windows machine.

1. Build the packaged desktop app:

```powershell
.\build_desktop.ps1
```

2. Share only the packaged output from:

- `desktop_release\PWPDesktopApp.exe`
- `desktop_release\PWPDesktopApp.zip`
- `desktop_release\CLIENT_README.txt`

3. Do not share the `.py` source files with clients.

## Desktop Update Flow

- Desktop app version is stored in `New PWP Bot.py`
- Update metadata is stored in `desktop_release.json`
- Users get update checks on startup and from `Help -> Check for Updates`
- Packaged desktop app can now download the latest ZIP, replace local files, and restart automatically
- For a new desktop release:
  - increase the app version
  - update `desktop_release.json`
  - rebuild the `.exe`
  - upload `PWPDesktopApp.zip` to GitHub Releases using the same filename every time

## Render Deployment

1. Push this project to GitHub.
2. Create a new Web Service on Render.
3. Connect the GitHub repository.
4. Render will detect `render.yaml` and `Dockerfile`.
5. Add environment variables if you want to override defaults from `.env.example`.
6. Deploy the service.

## Recommended Environment Values

- `PWP_HEADLESS=1`
- `PWP_BROWSER=chrome`
- `CHROME_BIN=/usr/bin/chromium`
- `CHROMEDRIVER_PATH=/usr/bin/chromedriver`
- `FLASK_DEBUG=0`

## Important Deployment Notes

- Uploaded files and generated output files are stored on the app filesystem.
- On Render free/basic instances, filesystem storage is temporary and should be treated as non-permanent.
- This version is designed for single-user usage without a database.
- Long-running bot actions now execute as background jobs and can be tracked from the web UI.

## Important Portal Limitation

- If the CPCB portal requires captcha or manual verification during login, a fully headless deployed server may not be able to complete login automatically.
- Local mode works better for captcha because you can see the browser and act manually.
- If captcha is enforced in production, you may need one of these:
  - a manual local operator flow
  - a remote browser session you can view
  - a supported API-based integration instead of Selenium

## Next Production Upgrades

- Add permanent file storage such as S3 or Cloudinary
- Add authentication for your own app
- Add database-backed job history if you want multi-user usage

## Code Visibility Note

- Server deployment protects code best because users never receive backend files.
- Desktop `.exe` packaging hides source better than sharing `.py` files, but it is not perfect protection against reverse engineering.
- For the current CPCB login flow, desktop packaging is the practical option when visible user-side browser interaction is required.
