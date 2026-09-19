# Taxi and Fly — Google Ads setup

## Προτεινόμενο Final URL (χωρίς redirects)

Χρησιμοποίησε **ένα** από αυτά (όλα είναι flat HTML, χωρίς 301):

| URL | Σημείωση |
|-----|----------|
| `https://taxiapp2026.github.io/TAXIdriverApp/ads.html` | **Προτεινόμενο** για νέα διαφήμιση |
| `https://taxiapp2026.github.io/TAXIdriverApp/get.html` | Ίδιο περιεχόμενο |
| `https://taxiapp2026.github.io/TAXIdriverApp/athens-airport.html` | Flat alias (όχι `/athens/airport`) |
| `https://taxiapp2026.github.io/TAXIdriverApp/download-app.html` | Flat alias (όχι `/download/app`) |

**Μην** βάλεις Final URL:

- το root booking SPA (`…/TAXIdriverApp/` ή `…/taxi-client-app/`)
- path χωρίς trailing slash τύπου `…/athens/airport` (κάνει **301**)
- απευθείας App Store / Play Store σε Search campaign

Display path: κράτα το ίδιο domain με το Final URL.

## Πριν το Request review

1. Ενεργοποίησε **GitHub Pages** στο repo `TAXIdriverApp` → Settings → Pages → Deploy from branch `main` (ή αυτό το PR branch μετά το merge) → folder `/ (root)`.
2. Άνοιξε το Final URL σε incognito: πρέπει να φορτώνει **200**, χωρίς redirect, με logo, κουμπιά stores, email και Privacy.
3. Στο Google Ads → Ads → Status → **Edit** Final URL αν χρειάζεται → **Request review**.

## Αν θες να κρατήσεις το παλιό domain (`taxi-client-app`)

Αντίγραψε από αυτό το repo στο `taxi-client-app` (branch `master`):

- `ads.html`, `get.html`, `athens-airport.html`, `download-app.html`
- `athens/airport/index.html` + `athens/airport/logo.png`
- `download/app/index.html` + `download/app/logo.png`
- `logo.png`, `privacy.html`, `robots.txt`

Μετά άλλαξε τα `canonical` / `og:url` / `og:image` από `TAXIdriverApp` σε `taxi-client-app`.

Final URL τότε: `https://taxiapp2026.github.io/taxi-client-app/ads.html`

## Τι διορθώθηκε για τα Ads policies

- Χωρίς auto-redirect σε store (destination mismatch)
- Flat URLs χωρίς GitHub Pages 301
- Logo τοπικά σε κάθε nested path (όχι 404)
- Ορατή επωνυμία **Taxi and Fly**, περιοχή (Αθήνα), email επικοινωνίας, Privacy Policy
- Ίδιο brand σε title / H1 / meta

## Tracking (προαιρετικό)

Όταν έχεις Google Ads Conversion ID (`AW-…`), πρόσθεσέ το στο `<head>` του `ads.html`:

```html
<script async src="https://www.googletagmanager.com/gtag/js?id=AW-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'AW-XXXXXXXXXX');
</script>
```

## Account

Χρησιμοποίησε το Ads account: `taxiandfly.privacy@gmail.com`
