# Web map readiness

Generated from the canonical Markdown records by `pipeline/export_web.py`.
A reference-ready record has text and a coordinate. A practice-ready record
also requires reviewed content, a verified coordinate, source metadata and a
concise model answer. No readiness flag is inferred from `status: sourced`.

The model answer is condensed from the entry's own anchors by
`pipeline/exam_notes.py`, which lifts clauses whole and never paraphrases, so
it inherits the body's accuracy and nothing beyond it. `modelAnswerSource`
distinguishes a condensed note from one written by hand in the frontmatter as
`model_answer_30`. A condensed note is a reference answer to reveal after
recall, not a mark scheme to grade a student's wording against.

A coordinate counts as verified when `coords_provisional` is `false`, meaning
someone checked it against a gazetteer. `coords_confidence` is not used as a
quality signal: it records how cleanly the dot was read off the scanned sheet,
not how close the reading is. Burzahom is labelled `high` and lies 139 km from
Burzahom. Measured against the unambiguous Wikidata entries inside the sheet's
frame, verified coordinates run to a median of 0.0 km and a p90 of 2.2 km
(n=123), which is what the 25 km accepted radius is built on; unverified ones
are exported with `scorable: false` and no radius at all.

## Summary

- Sites: **480**
- Reference ready: **480**
- Practice ready: **0**
- Scorable coordinates: **306**
- Unverified coordinates: **174**
- Missing state/region: **22**
- Unknown coordinate-confidence values: **0**
- Shared-coordinate groups needing review: **6**
- Location types needing review: **33**
- Missing source metadata: **51**
- Missing written source line: **63**
- Content reviews required: **480**
- Missing 30-word model answers: **0**
- Model answers condensed from the entry: **480**
- Model answers written by hand: **0**
- Legacy `data/sites.json` name mismatches: **13**
- Orphan gazetteer entries: **7**
- Unmatched PYQ labels: **166** (203 occurrences)
- PYQ labels resolved through unique answer aliases: **8** (15 occurrences)

## Exact coordinate collisions

These are review items, not automatic duplicates. Some may legitimately refer
to the same historical place.

| Coordinates | Records |
|---|---|
| `14.0919, 75.411` | `kambadahalli`, `shravanabelagol` |
| `20.8258, 76.6505` | `paithan-or-pratishthana`, `apegaon-janeshwar`, `paithan-eknath` |
| `22.6372, 77.7647` | `adamgadh`, `adam` |
| `24.9049, 82.304` | `kakoria`, `varanasi-ramananda-kabir-rai-ravidas` |
| `26.0055, 90.3582` | `kamakhya`, `pragjyotishpura` |
| `26.1999, 74.7146` | `ajmer-hakra-basin`, `ajmer-sharif` |

## Canonical-name mismatches

| Slug | Legacy index | Canonical Markdown |
|---|---|---|
| `bhitari-pillar-ghazipur` | Bhitari pillar Ghazipur | Bhitari (Ghazipur) |
| `hathigumpa` | hathigumpa | Hathigumpha |
| `kudumiyamalai-inscription` | Kudumiyamalai Inscription | Kudumiyamalai |
| `nanaghat` | nanaghat | Nanaghat |
| `shajahanpur` | Shajahanpur | Banskhera (Shahjahanpur) |
| `amarkantak1` | Amarkantak1 | Amarkantak |
| `jagganath-and-konark-sun-temple` | Jagganath and Konark Sun temple | Jagannath and Konark Sun Temple |
| `khatarmal` | Khatarmal | Katarmal Sun Temple |
| `masrur-rock-cut-temple` | masrur rock cut temple | Masrur Rock-cut Temple |
| `thirunadhikkara` | Thirunadhikkara | Thirunandikkara |
| `udaigiri-in-mp` | Udaigiri in MP | Udayagiri (Vidisha) |
| `shah-hamdam` | Shah Hamdam | Shah-e-Hamadan (Srinagar) |
| `tatha` | Tatha | Thatta |

## Missing state or region

- `ajmer-hakra-basin` — Ajmer(Hakra Basin)
- `anangpur` — Anangpur
- `dari-dungari` — Dari Dungari
- `gudiyam-caves` — Gudiyam Caves
- `gumarwin` — Gumarwin
- `hiran-valley` — Hiran Valley
- `hunasgi` — Hunasgi
- `lakhudiyar` — Lakhudiyar
- `lingsugur-same-as-maski-1st-palae-site-to-be-discovered` — Lingsugur- Same as Maski 1st palae site to be discovered
- `luni-valley` — Luni Valley
- `nashik` — Nashik
- `palakkad` — Palakkad
- `balathal` — Balathal
- `bangarh` — Bangarh
- `imlidih` — Imlidih
- `inamgaon` — Inamgaon
- `jorve` — Jorve
- `narhan` — Narhan
- `ojiyana` — Ojiyana
- `senaur` — Senaur
- `nagarjunakonda` — Nagarjunakonda
- `nartiang` — Nartiang

## No source metadata

No work in `corpus/` was confirmed to discuss these. `pipeline/cite.py
search "<name>"` finds passages; attach a key only after reading one.
A high score is not a confirmation — the top hit for Ajmer (Hakra Basin)
scored 40 and was about the conquest of Ajmer in 1195.

- `adiyala` — Adiyala
- `ajmer-hakra-basin` — Ajmer(Hakra Basin)
- `bhandarpur` — Bhandarpur
- `dari-dungari` — Dari Dungari
- `gumarwin` — Gumarwin
- `kibbanahalli` — Kibbanahalli
- `lingsugur-same-as-maski-1st-palae-site-to-be-discovered` — Lingsugur- Same as Maski 1st palae site to be discovered
- `malprabha-ghatprabha-valley` — Malprabha Ghatprabha valley
- `mandla` — Mandla
- `pahalgam` — Pahalgam
- `palakkad` — Palakkad
- `sabarmati-valley` — Sabarmati Valley
- `shivalik` — Shivalik
- `tiruvakkarai` — Tiruvakkarai
- `gungeria` — Gungeria
- `ojiyana` — Ojiyana
- `saipal` — Saipal
- `sukta-koh` — Sukta-koh
- `banimilia-banhera` — Banimilia Banhera
- `kuntitoli` — Kuntitoli
- `nartiang` — Nartiang
- `porkalam` — Porkalam
- `veerapuram` — Veerapuram
- `shalozan` — Shalozan
- `chak-86` — Chak 86
- `prahladpur` — Prahladpur
- `viratnagar` — Viratnagar
- `belum-caves` — Belum Caves
- `bojjana-konda-caves` — Bojjana Konda Caves
- `dambulla-cave-temple` — Dambulla Cave temple
- `hemis-gompa-monastery` — Hemis gompa Monastery
- `jagaddala` — Jagaddala
- `kesariya` — Kesariya
- `key-gompa-monastery` — Key Gompa Monastery
- `lalitgiri` — Lalitgiri
- `lamayuru-monsatery` — Lamayuru Monsatery
- `paro-monastery` — Paro Monastery
- `saspul-caves` — Saspul Caves
- `somapura` — Somapura
- `takh-i-bhai-monastery` — Takh-i Bhai Monastery
- `tawang-gompa-monastert` — Tawang gompa Monastert
- `thanale-caves` — Thanale Caves
- `thikse-monastery` — Thikse Monastery
- `akota` — Akota
- `dhanesar` — Dhanesar
- `brahmagir-jatinga-rameshwara-and-siddapur` — Brahmagir, Jatinga rameshwara and Siddapur
- `laghman-minor-re` — Laghman Minor RE
- `lampaka-minor-re` — Lampaka Minor RE
- `lauria-nandangarh-and-lauriya-araraj` — Lauria Nandangarh and Lauriya Araraj
- `nittur-and-udegolam` — Nittur and Udegolam
- `palkigundu-and-gavimath` — Palkigundu and gavimath

## Location type review

- `ajmer-hakra-basin` — Ajmer(Hakra Basin)
- `didwana-or-nagaur` — Didwana or Nagaur
- `hiran-valley` — Hiran Valley
- `luni-valley` — Luni Valley
- `malprabha-ghatprabha-valley` — Malprabha Ghatprabha valley
- `mogara-hills` — Mogara Hills
- `sabarmati-valley` — Sabarmati Valley
- `sohan-valley` — Sohan Valley
- `balaghat-or-mahurjhari` — Balaghat or Mahurjhari
- `bharatpur-or-noh` — Bharatpur or Noh
- `amravati-or-dharanikota` — Amravati or Dharanikota
- `potali-or-bodana` — Potali or Bodana
- `rajouri-or-rajapura` — Rajouri or Rajapura
- `tabo-caves-and-monastery` — Tabo Caves and monastery
- `tamluk-or-tamralipti` — Tamluk or Tamralipti
- `brahmagir-jatinga-rameshwara-and-siddapur` — Brahmagir, Jatinga rameshwara and Siddapur
- `girnar-or-jungadh` — Girnar or Jungadh
- `lauria-nandangarh-and-lauriya-araraj` — Lauria Nandangarh and Lauriya Araraj
- `nittur-and-udegolam` — Nittur and Udegolam
- `palkigundu-and-gavimath` — Palkigundu and gavimath
- `sisupalgarh-or-dhauli` — Sisupalgarh or Dhauli
- `deogarh-or-lalitpur-dashavtar` — Deogarh or Lalitpur Dashavtar
- `ellora-or-kailasa` — Ellora or Kailasa
- `jagganath-and-konark-sun-temple` — Jagannath and Konark Sun Temple
- `nirppeyarru` — Nirppeyarru
- `kodungallur-or-mahodayapuram` — Kodungallur or Mahodayapuram
- `nagarjuna-hills-or-vijaypuri` — Nagarjuna Hills or Vijaypuri
- `paithan-or-pratishthana` — Paithan or Pratishthana
- `tagara-or-ter` — Tagara or Ter
- `thanesar-or-sthanisvara` — Thanesar or Sthanisvara
- `kalyani-or-basavakalyan` — Kalyani or Basavakalyan
- `vijayapura-or-bijapur` — Vijayapura or Bijapur
- `balkh-or-bactria` — Balkh or Bactria

## Orphan gazetteer entries

- `lakhudiar`
- `nashi-pandavleni-caves`
- `runnindei`
- `sarumaru`
- `sittanavasa`
- `tekkalakota`
- `uttirameru`

## PYQ labels resolved through unique answer aliases

Search-only and ambiguous aliases are deliberately excluded.

| PYQ label | Occurrences | Canonical record |
|---|---:|---|
| Tanjore | 4 | `thanjavur` |
| Cambay | 3 | `khambat` |
| Gangaikon-dacholapuram | 2 | `gangaikonda-cholapuram` |
| Madura | 2 | `madurai` |
| Calicut | 1 | `kozhikode` |
| Jorwe | 1 | `jorve` |
| Quilon | 1 | `kollam` |
| Surparaka | 1 | `sopara` |

## Highest-frequency unmatched PYQ labels

- Attock: 3
- Bayana: 3
- Chunar: 3
- Gaur: 3
- Ahmadnagar: 2
- Ancient capital: 2
- Ancient capital city: 2
- Ancient education centre: 2
- Ancient inscriptions site: 2
- Ancient petroglyphs site: 2
- Ancient seaport and trade centre: 2
- Archaeological site: 2
- Balasore: 2
- Brick temple site: 2
- Centre of School of art: 2
- Chalcolithic: 2
- Chanderi: 2
- Chaul: 2
- Chittor: 2
- Daman: 2
- Halebid: 2
- Harappan site: 2
- Jaunpur: 2
- Kanauj: 2
- Lakhnawati: 2
- Neolithic site: 2
- Orchha: 2
- Panipat: 2
- Raichur: 2
- Rajmahal: 2
- Rameshwaram: 2
- Stone age site: 2
- Surat: 2
- Aharara: 1
- Ahrnadnagar: 1
- Ajmer: 1
- Akhnur: 1
- Amaravati: 1
- Amarkot: 1
- Amban: 1
