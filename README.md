# Web-App-IdiomasUG

Web app para la realización de exámenes de regularización del nivel de diferentes idiomas, del Departamento de Idiomas de la Universidad de Guanajuato, Campus León

## Project structure

```
index.html            App shell: markup for all screens
css/
  tokens.css          Design tokens (colors, fonts, radii, shadows)
  base.css            Reset, shared components, keyframes, print styles
  screens/            One stylesheet per screen
js/
  app.js              Entry point: navigation and screen wiring
  config.js           App settings (timer, start screen, feedback, AI guard)
  state.js            Central app state
  data/               Question bank and UI copy
  lib/                DOM, typewriter helpers
  screens/            One module per screen (login, profile, instructions,
                      exam, results, certificate)
assets/               Images used by the app
docs/                 Reference documents (question source, brand guide)
design-reference/     Original Claude Design canvas prototype and its exports
                      (kept for visual reference; no longer the source of truth)
```

## Run

The app is a static site using ES modules, so it must be served over HTTP
(opening `index.html` directly with `file://` will not load the modules):

```sh
python3 -m http.server 8000
# then open http://localhost:8000
```
