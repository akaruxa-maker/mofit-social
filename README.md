# mofit-social

Automatsko objavljivanje na Instagram i Facebook za MoFIT Fitness Club i
adidas Sports Studio. Bez servera, bez pretplate, bez trećeg alata.

GitHub Action se budi **svakih 15 minuta**, pogleda `queue/`, i objavi sve
čije je vrijeme došlo. Objavljeno zapiše u `state/` da se ne ponovi.

---

## Što radi

| Mreža | Objava | Story | Reel | Carousel |
|---|---|---|---|---|
| Instagram | ✅ | ✅ | ✅ | ✅ |
| Facebook Page | ✅ | ✅ (foto) | — (ide kao video) | ✅ |

**Što API ne može:** Highlightove. Meta nema endpoint za njih. Storyji se
objave automatski, a Highlight se jednom složi rukom s mobitela (10 minuta)
— nakon toga se ne dira.

---

## Postavljanje — jednom, oko 20 minuta

### 1. Repozitorij
Napravi **javni** repo i ubaci ovaj sadržaj.

> Mora biti javan jer Meta povlači slike s `raw.githubusercontent.com` i
> traži javno dostupan URL. U repou su samo marketinške slike koje ionako idu
> u javnost. Ako to ne želiš, vidi *Alternativa za medije* dolje.

### 2. Meta aplikacija
1. developers.facebook.com → **My Apps** → **Create App** → tip **Business**
2. Dodaj proizvode **Facebook Login for Business** i **Instagram**
3. Traženi pristupi (permissions):
   `instagram_basic`, `instagram_content_publish`,
   `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`
4. U **Graph API Explorer** generiraj **User token** s tim pristupima
5. Zamijeni ga za **long-lived token** (traje 60 dana):
   ```
   GET /oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id=APP_ID
     &client_secret=APP_SECRET
     &fb_exchange_token=KRATKI_TOKEN
   ```
6. Dohvati **Page token** (taj ne istječe dok je User token valjan):
   ```
   GET /me/accounts?access_token=DUGI_USER_TOKEN
   ```

### 3. Instagram ID-evi
```
GET /{PAGE_ID}?fields=instagram_business_account&access_token=PAGE_TOKEN
```
Vrati `instagram_business_account.id`. Upiši ga u `accounts.json`
(`ig:ass` i `ig:mofit`).

Instagram profil mora biti **Business** ili **Creator** i povezan s Facebook
stranicom. Oba već jesu.

### 4. Token u GitHub
Repo → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret**

| Ime | Vrijednost |
|---|---|
| `META_TOKEN` | Page access token |

**Token se upisuje samo ovdje.** Ne ide u kod, ne ide u chat, ne ide u repo.

### 5. Proba
Repo → **Actions** → **Objavi** → **Run workflow** → uključi *dry run*.
Ispisat će što bi objavio, bez objavljivanja.

---

## Kako se dodaje objava

Jedan `.json` u `queue/`. Ime datoteke je svejedno, `id` mora biti jedinstven.

```json
{
  "id": "2026-10-05-ass-ig-raspored",
  "when": "2026-10-05T21:00:00+02:00",
  "targets": ["ig:ass", "fb:ass"],
  "type": "post",
  "media": ["media/nesto.jpg"],
  "caption": "Tekst objave."
}
```

| Polje | |
|---|---|
| `id` | jedinstven; `state/<id>.json` sprječava dvostruku objavu |
| `when` | ISO 8601 s vremenskom zonom. `+02:00` ljeti, `+01:00` zimi |
| `targets` | `ig:ass`, `ig:mofit`, `fb:ass`, `fb:mofit` |
| `type` | `post`, `story`, `reel` |
| `media` | putanje u repou, ili puni javni URL-ovi |
| `caption` | tekst; Story ga ignorira |

**Preciznost vremena je 15 minuta** — toliko je razmak između pokretanja.
Ako treba točnije, promijeni `cron` u workflowu.

### Format medija
- **Slike: samo JPEG.** Meta ne prima PNG. Max ~8 MB.
- Feed 4:5 → 1080×1350 · Story i Reel 9:16 → 1080×1920
- Video: MP4, H.264 + AAC. Reel do 90 s.

---

## Ograničenja koja treba znati

- **100 objava po Instagram računu u 24 sata.** Nije blizu.
- **Token traje 60 dana.** Podsjetnik u kalendar. Ako istekne, Action padne i
  GitHub pošalje mail.
- **GitHub Actions cron zna kasniti** nekoliko minuta kad je gužva. Za
  objavu u 21:00 to nije bitno.
- **Vremenska zona.** GitHub radi u UTC, `when` nosi zonu, pa je ljetno/zimsko
  računanje riješeno — ali samo ako ga upišeš.

### Alternativa za medije (ako repo mora biti privatan)
U `MEDIA_BASE_URL` stavi bilo koji javni URL — npr. mapu na `mofit.hr` ili
Wix media. Skripta prihvaća i pune URL-ove u polju `media`, pa repo tada
sadrži samo tekst i raspored.

---

## Ručno pokretanje
```bash
export META_TOKEN=...
export MEDIA_BASE_URL=https://raw.githubusercontent.com/KORISNIK/mofit-social/main
python3 publish.py --dry-run
python3 publish.py
```

Bez vanjskih biblioteka — samo Python 3.
