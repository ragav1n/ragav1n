<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.svg">
  <img alt="Ragav. Security, systems, detection." src="assets/banner-light.svg" width="900">
</picture>

I create tools that run on your own machine.

Most of my time goes to [threat-intel](https://github.com/ragav1n/threat-intel), an IOC pipeline
that keeps report data on the host, and [ink2digital](https://github.com/ragav1n/ink2digital),
which turns handwritten German lecture slides into typeset LaTeX.

### Work

[**threat-intel**](https://github.com/ragav1n/threat-intel) · Python, FastAPI, MongoDB<br>
Pulls indicators from 102 configured sources, verifies and summarises them with local LLMs
through Ollama, links them into a knowledge graph and groups them into campaigns. Ships a
Next.js dashboard and a Docker stack.

[**ink2digital**](https://github.com/ragav1n/ink2digital) · Python, PyTorch<br>
Finds the handwriting on a photographed lecture slide, reads the German text and the maths, then
replaces the ink with typeset output. YOLOv8x for detection, TrOCR and TAMER for recognition,
meta-learning so it adapts to a new lecturer from a handful of examples.

[**novira**](https://github.com/ragav1n/novira) · TypeScript, Next.js, Capacitor<br>
Splits shared expenses and tracks budgets. I built it in Dortmund because I was fed up with
Excel. Live at [novira-one.vercel.app](https://novira-one.vercel.app), with iOS and Android builds.

[**look**](https://github.com/ragav1n/look) · TypeScript, React, Shopify<br>
Headless storefront for [look.ind.in](https://look.ind.in). React SPA on Vercel with Shopify
behind it, plus a serverless layer for the calls a public Storefront token cannot make.

[**patina**](https://github.com/ragav1n/patina) · Python<br>
Applies twelve digicam and camcorder looks to photos and video. Runs offline.

Smaller ones: [adaptive-firewall](https://github.com/ragav1n/adaptive-firewall) drives Suricata
and PF from a local LLM, [self-heal-sdn](https://github.com/ragav1n/self-heal-sdn) detects and
repairs network faults with LSTMs and isolation forests, and
[bip-rag](https://github.com/ragav1n/bip-rag) answers questions about utility contracts on-device.

### Elsewhere

[ORCID](https://orcid.org/0009-0001-7370-6173) ·
[LinkedIn](https://www.linkedin.com/in/ragavenderan-n) ·
[TryHackMe](https://tryhackme.com/p/R1gava) ·
[Hyperskill](https://hyperskill.org/profile/587003401) ·
[Google](https://g.dev/ragav1)
