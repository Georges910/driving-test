# Driving Theory Practice — Public Students / Private Admin

## Publish student site
1. Create a **public** GitHub repository and upload the **contents of this folder** to its root.
2. Repository Settings → Pages → Deploy from branch → main → /(root).
3. Share `https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/` with students.

## Enable private exam history
1. Create a **private Google Sheet** in your own Google account. Do **not** share it with students.
2. Sheet → Extensions → Apps Script. Replace `Code.gs` with `apps-script/Code.gs` from this project.
3. In Apps Script, click **+** → HTML, name it `Dashboard`, and paste `apps-script/Dashboard.html`.
4. Save. Deploy → New deployment → Web app → Execute as **Me**, Who has access **Anyone**. Authorize and copy the Web app `/exec` URL.
5. Set `SCORE_ENDPOINT` in public `config.js` to that URL; push your change to GitHub.
6. Reload the Google Sheet. Use **Driving Exam → Open Admin Dashboard** to see results, search by name, filter pass/fail and inspect attempts. The raw `Scores` sheet contains all saved entries.
7. Run a test exam, then check the Sheet. The browser cannot confirm persistence due to cross-origin `no-cors`; always verify the first test.

## Security and limitations
- Admin access is governed by **Google Sheet editor permissions**. No admin secret is published in GitHub or sent in URL query strings. Do not share the Sheet or Apps Script project with students.
- Public exam submissions are **not authenticated or independently verifiable**. A student could forge a result; suitable for practice history, not official examinations. Rate limiting/verified scoring requires a trusted backend.
- Google Apps Script `/exec` is publicly writable and can be abused; monitor Sheet growth and Apps Script quotas. No reliable server acknowledgment is available from the static frontend using `no-cors`.
- Names are collected: tell students their names, scores and exam dates are stored for training purposes; restrict access and set a retention policy.
- Repeated names are counted as one name in the summary, but cannot be reliably identified as the same person.
- Pass score and exam duration are configurable in `config.js`; verify official requirements before using them as official standards. Server currently expects 30 questions, 900 seconds and pass score 24; update validation in `Code.gs` if you change these settings.
