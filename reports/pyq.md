# What the map question has actually asked

Mined from the past papers in `corpus_pyq/`. Older papers name the
places; newer ones give only locational hints, so those contribute
chapter weights rather than site names.

- Map-question blocks: **17** naming places, **7** hint-only
- Distinct places named: **264**
- Matched to records: **89**
- Ambiguous labels held back for review: **1**
- Occurrences with page provenance: **337**

> **Year attribution is unreliable.** The 1979-2012 compendium prints
> many papers per page, so the year shown is the first one found on
> the page, not necessarily the paper the question came from. Treat
> the counts as trustworthy and the years as indicative.
>
> Every occurrence now carries the paper, page and block it was read
> from, in `data/pyq.json`. That is what makes a count auditable: two
> spellings of one place on one page would be one appearance, while
> the same place on two pages is two. Spot-checking the compendium,
> Madura and Madurai fall on four different pages — four papers, so
> four appearances, not two counted twice.

## Ambiguous — one label, several records

Not counted against any record. Resolve by adding a reviewed
alias, or by merging the records if they are the same place.

| Label | Times | Candidate records |
|---|---:|---|
| Paithan | 2 | `paithan-eknath`, `paithan-or-pratishthana` |

## Chapter weight from the hint-only papers

| Chapter | Hints |
|---|---:|
| Chalcolithic | 14 |
| Ancient Capitals and trade cities | 10 |
| Neolithic | 8 |
| Ancient Ports | 6 |
| Harappa | 6 |
| Mesolithic | 4 |
| Palaeolithic | 4 |
| Megalith | 3 |
| Buddhist Sites | 2 |
| Rockcut Caves | 1 |

## Most-asked places overall

| Place | Times |
|---|---:|
| Mandu | 4 |
| Tanjore | 4 |
| Attock | 3 |
| Bidar | 3 |
| Cambay | 3 |
| Champaner | 3 |
| Chunar | 3 |
| Multan | 3 |
| Bayana | 3 |
| Gaur | 3 |
| Ahmadnagar | 2 |
| Chittor | 2 |
| Jaunpur | 2 |
| Madura | 2 |
| Panipat | 2 |
| Rameshwaram | 2 |
| Sasaram | 2 |
| Surat | 2 |
| Thatta | 2 |
| Bijapur | 2 |
| Chanderi | 2 |
| Chaul | 2 |
| Gulbarga | 2 |
| Hampi | 2 |
| Kalpi | 2 |
| Kanauj | 2 |
| Raichur | 2 |
| Rajmahal | 2 |
| Brahmagiri | 2 |
| Burzahom | 2 |
