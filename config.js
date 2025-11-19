// Runtime configuration for the static site
// Set API_BASE_URL to the public backend endpoint when deployed to GitHub Pages.
// Leave empty for local development where the Flask backend runs on the same origin.

window.CONFIG = {
  // Local development: point to Flask backend
  API_BASE_URL: 'http://127.0.0.1:8001',
};