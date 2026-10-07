## Training text for a 355M fiction model: what exists and what to do first

I can't give you a clean, bulk source of modern strange prose ready to download, because I didn't find one. The modern gap gets filled from three places: things authors have explicitly let go, a few small grey archives, and asking. The largest new reservoir of text is mid-century public-domain prose (1930–63) through Harvard's Institutional Books dataset.

### 1. The shortlist (ranked)

| # | Source | What / era | Size | Label + quoted line | How to get it | Effort |
|---|---|---|---|---|---|---|
| 1 | **Institutional Books 1.0** (Harvard Library) | Harvard's scanned books. Copyright status comes from HathiTrust, so it includes US 1930–63 books HathiTrust opened after confirming they were never renewed. Mostly 19th–20th century. | 983K volumes / 242B tokens in total. **The 1930+ fiction subset is unknown.** | **Clean text, gated access:** "You may use the Service solely for noncommercial purposes"; "You may not share or redistribute." Fits private use. | Hugging Face `institutional/institutional-books-1.0`. It has `date1_src`, `genre_or_form_src` and `topic_or_subject_gen` fields to filter on. | Medium (large download) |
| 2 | **Escape Pod / PodCastle / PseudoPod** | Modern SF, fantasy and horror short fiction, 2005–today. Much of PodCastle and PseudoPod is literary-weird. | ~2,800 stories, ~12M words (**my estimate** from episode counts) | **Robots.txt blocks crawlers:** their robots.txt blocks GPTBot, CCBot and Google-Extended. Yet the text is "Attribution-Noncommercial-No Derivative Works 4.0". **The best thing to ask for.** | Ask (section 6) | Low if they say yes |
| 3 | **Rudy Rucker's free books** | Ware tetralogy, Postsingular, Juicy Ghosts, Spaceland, White Light, Jim and the Flims, Complete Stories, Journals. 1980s–2020s, gonzo-weird. | ~1.5M words of fiction (estimate). Journals extra. | **Clean, explicit permission:** "I want people to read these, and I want AIs and bots to read them, and to train on them." He forbids republishing or selling. | rudyrucker.com/blog/rudy-rucker-free-books | Low |
| 4 | **Small Beer Press CC books** (Kessel, McHugh, Rosenbaum, Vukcevich) | 2000s literary-weird short fiction | ~0.5M words (estimate) | **Licence clean, website says no:** "licensed under a Creative Commons (Attribution-NonCommercial-ShareAlike 3.0)". But smallbeerpress.com's robots.txt blocks GPTBot and CCBot. The CC version of Link's *Magic for Beginners* was taken down. | Ask them, then download | Low |
| 5 | **SmokeLong Quarterly** | Literary flash fiction, 2003–today. Sentence-conscious, often strange. | Low millions of words (estimate, not counted) | **Grey:** robots allows everyone (`crawl-delay: 20`); I found no AI statement | Slow crawl | Medium |
| 6 | **365tomorrows** | SF flash fiction of 600 words or less, daily since 2005. Quality varies. | Up to ~4M words (estimate: ~7,000 stories × ≤600 words) | **Grey:** "first electronic publication rights and non-exclusive subsequent publication rights. You retain ownership." Robots allows `*`, no AI rules. | Crawl (crawl-delay 10) | Low |
| 7 | **Cory Doctorow's CC novels and stories** | 2003–2010s. Plain prose rather than strange, but clean. | ~1M words (estimate) | **Clean:** CC BY-NC-SA / BY-NC-ND (licence checked from memory, not re-fetched); craphound.com robots has no AI blocks | craphound.com, also on Gutenberg | Low |
| 8 | **Gutenberg's "copyrighted, with permission" titles, plus the 1930 books** | Modern books the rights holders allowed onto Gutenberg. Works published in 1930 entered US public domain on 2026-01-01. | Count not verified | **Clean** | Filter the Gutenberg RDF catalogue for the copyrighted rights string; re-pull new releases | Low |
| 9 | **Unpublished 1930–63 pulp and digest magazines** (Internet Archive's Pulp Magazine Archive: 12,000+ issues, Galaxy, If) | 1930s–60s SF, crime, weird | Tens of millions of words before checks; the public-domain share after per-story checks is unknown. Overlaps heavily with Gutenberg. | **Grey:** uploads by users; I could not re-check archive.org's terms | Scans plus OCR text, messy two-column layout | High |
| 10 | **Web serials** (Unsong, Worm/Ward, A Practical Guide to Evil, The Wandering Inn) | 2010s. Large, but mostly not literary. | Sizes reported by the authors, not verified | **Grey:** wordpress.com / own-site robots have no AI blocks. I did not check what the authors have said about AI. | Crawl | Medium |

**Sites whose robots.txt or terms say no to crawlers or training (checked this session):**
- Royal Road, Archive of Our Own, Wattpad, SpaceBattles, Sufficient Velocity, The Dark, Weird Horror, BOMB, Paris Review, Baen: robots.txt blocks AI crawlers.
- Smashwords: "expressly forbids scanning, scraping, and analysis of the Site and any book contents for AI training purposes, whether books are purchased or free."
- Weightless Books: "We're strongly against the use of 'AI' in art or writing."
- Electric Literature: its terms forbid using automated processes to "data-mine, data-crawl, scrape".
- Orion's Arm: "Any use… other than for private, non-commercial viewing purposes is strictly prohibited."
- Reddit, and so the r/WritingPrompts and r/nosleep datasets: robots.txt returns a "Blocked" page.
- Daily Science Fiction: the archive is gone; the site says "Launching Soon".
- Free SF Online (freesfonline.net): its own robots blocks AI bots, but it is a useful index for checking story hosts one by one.

**Open but no use for the gap:** Common Pile, Common Corpus, Standard Ebooks, PG-19 and US-PD-Books are all public domain by date, so almost nothing after 1929. Common Pile also leaves out NC/ND licences on purpose, so it can't hold the CC-NC modern fiction. The Internet Archive asked for US-PD-Books to be taken down because its metadata was "too unreliable" for public-domain calls, and the full texts were removed.

### 2. What the scene does

**Small from-scratch builders mostly don't train on books.** They use FineWeb or FineWeb-Edu. A typical post, "235M param LLM from scratch on a single RTX 5080" (r/LocalLLaMA, 2026-04): "Data from FineWeb-Edu, Wikipedia, StackExchange, code, and ArXiv." [reddit.com/r/LocalLLaMA/comments/1srsxqs/]

**The prose-minded ones go by era, to stay out of copyright.** TimeCapsuleLLM trains only on 1800s text: "40B tokens or 160GB of 1800-1875 english data" [1uswlq8]. A commenter there: "I had thought about collecting material up to the point that copyright had expired to avoid legal/ethical questions."

**BabyLM is small and mostly not literary.** The 2024 strict track was CHILDES 29M words, BNC dialogue 8M, Gutenberg children's stories 26M, OpenSubtitles 20M, Simple Wikipedia 15M, Switchboard 1M.

**The grey history matters.** BookCorpus was scraped from Smashwords' free books without permission, and Smashwords now forbids training outright. books3 is a pirate set. Court filings in Bartz showed Anthropic downloaded over 7M books from LibGen and PiLiMi. The careful projects are Common Pile/Comma, Pleias/Common Corpus and Institutional Books. All three solved the problem by staying pre-1930, which is why the modern gap stays empty.

I couldn't do the reddit survey properly. Arctic Shift full-text search timed out on every query; only title searches and fetching single threads worked. So this section rests on a few threads, not a sweep.

### 3. The unrenewed-copyright route

It is real, but it is mostly a route to mid-century books, not to modern prose.

- **The scale:** Leonard Richardson's analysis of the NYPL renewal data found "73% have no renewal record at all" for the pre-1964 books where renewal matters. The data is on GitHub as `leonardr/cce-python` and `cce-spreadsheets`.
- **HathiTrust's review:** by 2016 it had made 632K copyright determinations, about 53% public domain, now open in full view.
- **The catch for individuals:** HathiTrust's bulk datasets of Google-scanned books need an institution that has signed with Google. **Institutional Books is the way around that,** because it inherits HathiTrust's determinations.
- **Magazines are a trap.** The Online Books Page's renewals list warns: "even though a particular magazine issue was not renewed, a contribution appearing in it might have been." For example, *If*: "no issue renewals found… contributions actively renewed from March 1952." *Galaxy*: contributions renewed from October 1950. So every story needs its own check. Gutenberg's volunteer proofreaders have already done this for thousands of stories, and your pulp shelf probably holds them. The new yield beyond that is unknown and costly.

### 4. The buying route

- **The law:** Bartz v. Anthropic (N.D. Cal., June 2025) held training "exceedingly transformative" fair use, and destructively scanning books Anthropic had bought was fair use too. Pirated copies were not cleared. This is one district judge in the US, it doesn't bind anyone else, and you're training from Vietnam, where it has no direct force.
- **Price:** StoryBundle right now is $30 for 15 books, so $2 a book. Its terms forbid "copying, distributing… any part of the Products… including… 'scraping'". That reads as a redistribution ban, and I found no AI clause, so: grey. Humble: I couldn't fetch its terms.
- **Who says no in their terms:** Smashwords and Weightless (quotes above). Penguin Random House books printed since 2024 say "No part of this book may be used or reproduced in any manner for the purpose of training artificial intelligence technologies or systems". Their terms say no.
- **What it costs in tokens** (estimate): one novel is ~120K tokens, so 5M tokens is ~40 books. Bundles cost ~$80 per 5M tokens, but their taste is indie genre. Small-press titles chosen for taste, at ~$8, cost ~$320 per 5M tokens.

### 5. The synthetic route

People do generate fiction corpora, but for simple language, not literary quality. The documented failure is sameness. The SimpleStories paper found "59% of [TinyStories] stories contain the string 'Once upon a time' verbatim", and fixed it by varying the prompt parameters on purpose. Even fixed, what you get is the generating model's mode: its rhythm, its pet words, its tidy endings. Generated text loses the rare tails of the distribution, and the rare tails are exactly what you want. My view: synthetic text can teach structure, at most a small slice. As a source of strangeness it teaches magdra to sound like the teacher. Don't spend the 5M-token increments on it.

### 6. What we were missing — do these first

1. **Institutional Books metadata pass.** Accept the gate, pull the metadata only, and count English volumes dated 1930–1977 with fiction or literature subjects. That's an hour to a real number, and it's the only clean source that could reach tens of millions of tokens.
2. **Three asks:**
   - Escape Artists: the largest prize, already CC BY-NC-ND, so "private, non-commercial, never redistributed" is close to what they already allow.
   - Small Beer: CC-friendly, but its site blocks AI crawlers.
   - Rucker: needs no ask, just take it.

   Template: who you are, the art project, private and never redistributed, non-commercial, which texts, that you'll take no for an answer, and that you'll delete on request.

   I found no documented case of a small magazine granting private training permission. The only precedents are big publisher deals: HarperCollins pays $2,500 per title, opt-in. Rucker is the only author I confirmed.
3. **Take the clean small sources now:** Rucker, Doctorow, Gutenberg's permission titles and its 1930 releases. Add SmokeLong and 365tomorrows only if you accept grey.

**Couldn't verify:**
- How much 1930+ fiction Institutional Books actually holds
- Whether Escape Artists publishes full text for every episode, and its contract terms on AI
- Humble's terms, the Internet Archive's current terms, and Fireside's content signal (robots has comments only)
- How many "copyrighted with permission" titles Gutenberg has
- Web serial word counts and their authors' positions on AI
- Every size marked "estimate"

Sources: [Institutional Books](https://huggingface.co/datasets/institutional/institutional-books-1.0) · [US-PD-Books](https://huggingface.co/datasets/storytracer/US-PD-Books) · [Common Pile](https://huggingface.co/blog/common-pile/common-pile-v0p1-announcement) · [Common Corpus](https://huggingface.co/datasets/PleIAs/common_corpus) · [Rucker free books](https://www.rudyrucker.com/blog/rudy-rucker-free-books/) · [Escape Pod about](https://escapepod.org/about/) · [Small Beer CC](https://smallbeerpress.com/creative-commons/) · [365tomorrows about](https://365tomorrows.com/about/) · [Periodical first renewals](https://onlinebooks.library.upenn.edu/cce/firstperiod.html) · [Richardson on renewals](https://www.crummy.com/2019/8) · [HathiTrust datasets](https://hathitrust.org/datasets) · [IA pulp/Galaxy](https://archive.org/details/galaxymagazine) · [Bartz summary](https://www.akingump.com/en/insights/ai-law-and-regulation-tracker/district-court-rules-ai-training-can-be-fair-use-in-bartz-v-anthropic) · [PRH clause](https://thebookseller.com/news/penguin-random-house-underscores-copyright-protection-in-ai-rebuff) · [HarperCollins deal](https://thebookseller.com/news/harpercollins-signs-contract-with-tech-company-to-use-limited-number-of-titles-to-train-ai) · [SimpleStories](https://arxiv.org/abs/2504.09184) · [BabyLM 2024](https://arxiv.org/html/2404.06214v2) · [StoryBundle terms](https://storybundle.com/terms) · [Smashwords ToS](https://www.smashwords.com/about/tos) · [Weightless FAQ](https://weightlessbooks.com/faq/)