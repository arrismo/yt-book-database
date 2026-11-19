# Reading Room Caption Finder

Cross-browser extension that reads visible YouTube captions and sends recent caption windows to the Reading Room Worker for deterministic book-title matching.

## Load locally

- The deployed endpoint is prefilled: `https://the-reading-room.mikaelmoise00.workers.dev/api/caption-match`.
- Chrome: open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select `extension/`.
- Firefox: open `about:debugging#/runtime/this-firefox`, choose **Load Temporary Add-on**, and select `extension/manifest.json`.
- Open a YouTube video, enable captions, and watch. Matches appear in the extension popup.
