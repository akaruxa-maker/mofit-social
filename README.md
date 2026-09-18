# mofit-social

Automatsko objavljivanje na Instagram i Facebook za MoFIT Fitness Club i
adidas Sports Studio. Bez servera, bez pretplate, bez trećeg alata.

GitHub Action se budi **svakih 15 minuta**, pogleda mapu `queue/`, i objavi
sve čije je vrijeme došlo. Objavljeno zapiše u `state/` da se ne ponovi.

---

## ✅ Već napravljeno

- Repo, kod, mediji i prvih 7 objava u redu čekanja
- GitHub Pages uključen → slike i videi su na
  `https://akaruxa-maker.github.io/mofit-social/media/...`
- Skripta sama pronalazi Instagram ID iz povezane Facebook stranice,
  pa nema ručnog upisivanja brojeva

## ⬜ Ostalo za napraviti — tri koraka

### 1. Potvrdi Meta developer račun
`developers.facebook.com` trenutno traži **„Confirm Account"**. Dok se to ne
riješi, aplikacija se ne može napraviti. Klikni gumb i prođi korake.

### 2. Napravi Meta aplikaciju i token
1. `developers.facebook.com` → **My Apps** → **Create App**
2. Tip: **Business**
3. Dodaj proizvode **Facebook Login for Business** i **Instagram**
4. Otvori **Tools → Graph API Explorer**
5. Gore desno odaberi svoju aplikaciju
6. Pod **Permissions** dodaj:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_posts`
7. **Generate Access Token** → odobri obje stranice (MOFIT i adidas Sports Studio)
8. U padajućem izborniku **User or Page** odaberi **Page → MOFIT**
9. Kopiraj token koji se pojavi

> Token je lozinka. Ne šalji ga nikome i ne upisuj ga u kod.

### 3. Upiši token u GitHub
Repo → **Settings** → **Secrets and variables** → **Actions** →
**New repository secret**

| Ime | Vrijednost |
|---|---|
| `META_TOKEN` | token iz koraka 2 |

### 4. Proba
Repo → **Actions** → **Objavi** → **Run workflow** → uključi *dry run* → pokreni.
Ispisat će što bi objavio, bez objavljivanja. Ako piše `DRY` i popis objava,
sve radi.

---

## Ako Action padne s porukom o Instagramu

> `Facebook stranica X nema povezan Instagram poslovni racun`

Znači da Instagram profil nije povezan s Facebook stranicom. Popravlja se u
Instagram aplikaciji: **Postavke → Accounts Center → Povezani računi** ili na
Facebook stranici: **Settings → Linked accounts → Instagram**.

Instagram profil mora biti **Business** ili **Creator**, ne osobni.

---

## Što sustav zna objaviti

| Mreža | Objava | Story | Reel | Carousel |
|---|---|---|---|---|
| Instagram | ✅ | ✅ | ✅ | ✅ |
| Facebook stranica | ✅ | ✅ (foto) | kao video | ✅ |

**Highlightove API ne podržava.** Meta za njih nema sučelje. Storyji se objave
automatski, a Highlight se jednom složi rukom s mobitela i poslije se ne dira.

---

## Kako se dodaje objava

Jedan `.json` u mapu `queue/`. Ime datoteke je svejedno, `id` mora biti jedinstven.

```json
{
  "id": "2026-10-05-ass-raspored",
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
| `when` | ISO 8601 sa zonom. `+02:00` ljeti, `+01:00` zimi |
| `targets` | `ig:ass`, `ig:mofit`, `fb:ass`, `fb:mofit` |
| `type` | `post`, `story`, `reel` |
| `media` | putanje u repou, ili puni javni URL-ovi |
| `caption` | tekst; Story ga ignorira |

Preciznost vremena je 15 minuta — toliko je razmak između pokretanja.

### Format medija
- **Slike: samo JPEG.** Meta ne prima PNG. Max ~8 MB.
- Feed 4:5 → 1080×1350 · Story i Reel 9:16 → 1080×1920
- Video: MP4, H.264 + AAC. Reel do 90 s.

---

## Što treba znati

- **Token traje 60 dana.** Stavi podsjetnik u kalendar. Kad istekne, Action
  padne i GitHub pošalje mail.
- **100 objava po Instagram računu u 24 sata.** Nije blizu.
- GitHub Actions cron zna kasniti par minuta kad je gužva.
- Repo je javan jer Meta povlači medije s javnog URL-a. U njemu su samo
  marketinške slike koje ionako idu u javnost.

## Ručno pokretanje
```bash
export META_TOKEN=...
export MEDIA_BASE_URL=https://akaruxa-maker.github.io/mofit-social
python3 publish.py --dry-run
```
Bez vanjskih biblioteka — samo Python 3.
