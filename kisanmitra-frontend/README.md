# AgriPulse web app (kisanmitra-frontend)

The React front end of **AgriPulse (KisanMitra AI)**: an AI farming companion with leaf disease detection,
mandi price forecasts, weather advice, an equipment marketplace, a loan advisor, an assistant and voice
in 14 languages. It talks to the FastAPI backend in the parent folder. The full project description is in the
[root README](../README.md).

Built with Create React App, React 19, Framer Motion (animation) and Lucide (icons). There is no router
library and no CSS framework: the design system is plain CSS with tokens for light and dark themes.

## Run it

```powershell
npm install
npm start          # http://localhost:5555  (the port comes from .env)
```

The backend must be running for anything except the splash and the story page
(`python -m uvicorn app.main:app --reload --port 5556` from the project root).

| Script | What it does |
|---|---|
| `npm start` | dev server with reload |
| `npm test -- --watchAll=false` | 35 tests (React Testing Library, fake backend) |
| `npm run build` | production build into `build/` |

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `REACT_APP_API_URL` | URL of the backend, no trailing slash | `http://127.0.0.1:5556` |
| `PORT` | dev server port | `5555` |

Copy `.env.example` to `.env` to change them. `REACT_APP_*` values are baked in at **build time**: after
changing one on a host such as Vercel, redeploy. The backend must list this app's address in its
`CORS_ORIGINS`.

## How the app flows

1. **Splash** (`Splash.js`): the AgriPulse lockup animation in the app's green palette.
2. **Story page** (`Landing.js`): a public, scrollable page (hero, about, six tools, how it works, languages)
   with scroll-driven text, counters, card reveals and marquees.
3. **Frame** (`Site.js`): a hidden menu (three lines, top left) that drops as a curtain, and a profile panel
   (top right) that opens as a circular reveal.
4. **Login** (`AuthFlow.js`): phone + OTP, then a 3-step onboarding for new farmers. Opening a tool as a
   guest plays a colour transition into the login and returns to that tool afterwards.
5. **Tools** (`pages/` and `LoanAdvisor.js`): dashboard, disease scan, price forecast, weather,
   marketplace, assistant, history, loan advisor, profile.

`App.js` owns the session (token, user), the language, the theme, the assistant chat and the current page,
and decides which screen to show. Pages keep their own state.

## Folder guide

```
src/
  App.js            session, language, page switching, page transitions
  Splash.js         opening animation
  Landing.js        story page
  Site.js           header, menu panel, profile panel, footer
  AuthFlow.js       login, onboarding, profile editing
  LoanAdvisor.js    Kisan Credit Card advisor (4-step form and report)
  TrackingPanel.js  owners share equipment GPS position or create a tracker key
  voice.js          microphone input, spoken answers, voice commands, API_URL
  pages/            Home (dashboard), Disease, Price, Weather, Marketplace, Assistant, History, Profile
  ui/               kit.js (buttons, fields, modal, toasts, motion helpers), art.js (SVG scenes),
                    icons.js, notify.js (toast / confirm callable from anywhere)
  i18n/             14 label files and the t() helper
  styles/           base (tokens, components), art, auth, shell, pages, site
```

## Languages

English, Hindi, Kannada, Telugu, Tamil, Malayalam, Marathi, Bengali, Gujarati, Punjabi, Odia, Urdu
(right to left), Assamese, Bhojpuri.

- `src/i18n/<code>.json` holds the interface labels (menu, main buttons, placeholders, voice messages, page
  titles). All languages except Malayalam are hand-written, so please have a native speaker review them.
- A label missing from a language falls back to English, or is translated once by the server
  (`POST /i18n/translate`) and cached in the browser.
- To add a label, add it to `en.json`, use `t("key")` in the component, then add the translations.
- Text outside these labels (most page copy) is still English; answers, advice and spoken replies from the
  backend follow the chosen language.

## Voice and browser features

The microphone (voice input), camera (leaf photos) and geolocation (nearby equipment) need **HTTPS** or
`localhost`. Razorpay Checkout is loaded from `public/index.html`.

## Design notes

- Colours, radii and shadows are CSS variables in `styles/base.css`; the dark theme overrides them under
  `:root[data-theme="dark"]`, and the choice is stored in `localStorage`.
- Animation uses Framer Motion; users who prefer reduced motion get near-instant transitions.
- Layout is mobile first; the header is the same on every screen size.
- Toasts and confirm dialogs come from `ui/notify.js` (`notify(...)`, `confirmDialog(...)`): there are no
  browser `alert` popups.

## Tests

`src/App.test.js` renders the whole app against a small fake `fetch` backend. It covers the splash, the story
page, the menu and profile panels, login and onboarding, guest redirects, the language switch (including
Urdu direction), and each tool page. `setupTests.js` provides the browser features jsdom lacks
(`IntersectionObserver`, `matchMedia`) and a longer time limit for the page transitions.

## Deploy (Vercel)

Import the repository, set **Root Directory** to `kisanmitra-frontend`, keep the Create React App defaults
(`npm run build`, output `build`), and add `REACT_APP_API_URL`. Full steps are in
[`../docs/DEPLOY.md`](../docs/DEPLOY.md).
