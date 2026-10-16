# Remote mobile access (research)

Grocery Wizard runs as a **Streamlit** app (`just grocery-ui`) with **Notion** as the data store. Credentials live in `.env` (`NOTION_API_KEY`, database IDs).

| Where the app runs | Who can use it |
| --- | --- |
| **Local** (`just grocery-ui`, default localhost) | Anyone who can reach the URL — **no in-app login** (typical: only you on the Mac). |
| **Household deploy** (Streamlit Community Cloud, [#354](https://github.com/rachelgramlich/grocery-wizard/issues/354)) | **Google sign-in** + email allowlist (`GROCERY_WIZARD_REQUIRE_AUTH`, `GROCERY_WIZARD_AUTH_EMAIL_ALLOWLIST`) — see [household-deploy.md](../../../docs/household-deploy.md) and `access_gate.py`. |

This document compares ways to use the UI on a phone **outside home Wi‑Fi**, records a **household decision**, and points at remaining backlog work.

## Household decision (2026)

| Use case | Approach |
| --- | --- |
| **Default** | Run `just grocery-ui` on the Mac when it is on; use the **CLI** when the UI is not running. Optional: phone on **same Wi‑Fi** while the Mac is up (`just grocery-ui -- --server.address=0.0.0.0` if needed). |
| **Phone on cellular / anytime** | **Household deploy** on Streamlit Community Cloud ([#354](https://github.com/rachelgramlich/grocery-wizard/issues/354)) — see [household-deploy.md](../../../docs/household-deploy.md). Not tunnel-to-Mac—the laptop is often off. |

No committed Just recipes or config exist for tunnels or LAN bind; pass Streamlit flags yourself if you ever experiment locally.

## Requirements (implicit)

| Need | Notes |
| --- | --- |
| Phone browser from anywhere | HTTPS URL, not only `localhost` / LAN IP |
| Secrets stay out of git | Already true; hosted deploy needs platform secret store |
| Single household / low traffic | No multi-tenant product requirements |
| Notion is source of truth | Remote access does not require syncing `.local/` to the cloud for core flows; some session files may still be laptop-local |

## Options compared

### A. Tunnel to the machine running Streamlit

Run Streamlit on your Mac (or a home server) and expose it through a tunnel (Tailscale, Cloudflare Tunnel, ngrok, etc.).

| Approach | Pros | Cons |
| --- | --- | --- |
| **Tailscale** (or similar mesh VPN) | Private; secrets stay on your machine | Host must be **on**; VPN app on phone |
| **Cloudflare Tunnel** (`cloudflared`) | Stable HTTPS; optional **Cloudflare Access** in front | Host must be **on**; setup outside the repo |
| **ngrok / similar** | Fast to try | Ephemeral URLs on free tiers |

**Not chosen here:** with the Mac often off, tunnel-to-laptop does not meet “use the UI when I want from my phone.”

### B. Always-on hosted Streamlit

Deploy the same app to a PaaS (Railway, Fly.io, Render, a small VPS, etc.) or **Streamlit Community Cloud**.

| Approach | Pros | Cons |
| --- | --- | --- |
| **Streamlit Community Cloud** | Minimal ops; **in-app Google allowlist** shipped for household deploy (#354) | Public/community constraints; auth + secrets setup required |
| **Railway / Fly / Render / VPS** | Always on | Monthly cost; `NOTION_*` in platform secrets; **auth required** before a public URL; Dockerfile or build config |
| **Serverless** | — | Poor fit for Streamlit |

**Chosen path for remote UI:** Streamlit Community Cloud + app auth (#354), not tunnels to the Mac. ~~#138~~ / ~~#139~~ were planning issues superseded by #354.

### C. Mobile shell (PWA vs native)

| Approach | Pros | Cons |
| --- | --- | --- |
| **Mobile browser + “Add to Home Screen”** | No backend change | Streamlit is not a full PWA; offline does not work |
| **PWA metadata + UI pass** (#140) | More app-like launch | Does not replace hosting or auth |
| **Native wrapper** | Store presence | High cost for a personal tool |

## Recommendation

**Local:** use **local Streamlit + CLI** when the Mac is on; do **not** invest in tunnel-to-Mac automation in this repo.

**Remote / phone on cellular:** use the **household deploy runbook** ([#354](https://github.com/rachelgramlich/grocery-wizard/issues/354), [docs/household-deploy.md](../../../docs/household-deploy.md)). Treat Cloudflare Tunnel-to-Mac as a personal ops note only, not a product path.

**Defer:** Native app; Mac tunnel runbook (#137 — closed as not planned).

## Staged follow-up issues

| Phase | Backlog issue | Topic |
| --- | --- | --- |
| — | ~~[#137](https://github.com/rachelgramlich/grocery-wizard/issues/137)~~ | Mac tunnel runbook — **not planned** (Mac often off) |
| — | ~~[#138](https://github.com/rachelgramlich/grocery-wizard/issues/138)~~ | Superseded by #354 |
| — | ~~[#139](https://github.com/rachelgramlich/grocery-wizard/issues/139)~~ | Superseded by #354 (Google `st.login` + allowlist) |
| Done | ~~[#354](https://github.com/rachelgramlich/grocery-wizard/issues/354)~~ | SCC deploy, Google allowlist, GitHub feedback inbox |
| Deferred | [#140](https://github.com/rachelgramlich/grocery-wizard/issues/140) | Mobile UX: Add to Home Screen hints, optional PWA meta, touch layout pass |

## Security checklist (any public URL)

- [ ] Gate the URL — for SCC, enable **in-app auth** (`GROCERY_WIZARD_REQUIRE_AUTH` + allowlist) and keep the Cloud app **Private**; optional alternative is Cloudflare Access in front of a self-hosted URL.
- [ ] Keep `.env` / platform secrets out of git; rotate `NOTION_API_KEY` if it was ever leaked.
- [ ] Notion integration should only have access to the databases you intend.
- [ ] Optional: NYT cookies in `.env` are sensitive; same rules apply on a hosted machine.

## Manual smoke test (local UI only)

1. With `.env` set and Mac on: `just grocery-ui` → `http://localhost:8501` → Notion-backed tabs load.
2. If you need same-Wi‑Fi phone once: `just grocery-ui -- --server.address=0.0.0.0` and open the Mac’s LAN IP (no repo recipe required).

For hosted auth smoke tests, see [household-deploy.md](../../../docs/household-deploy.md).
