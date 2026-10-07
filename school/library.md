# the library

Three lists and two shelves: the library, which is bekh's own picks book by book, and beside it
since 2026-10-07 the anthology shelf (its own section below). The library is `inbox/clean/` — what has actually been converted
(`inbox/clean/ledger.jsonl` says what each file was, how many words, what was dropped and why;
`ls inbox/clean` is the count). bekh gets the books by hand into
`~/tower/ephemeral/booox/souls_lain_library/`; `data/books.py <folder> --out inbox/clean`
converts them (language gate, container check, trims; `inbox/skip.txt` for files never to
convert), `data/pages.py` joins a book that arrived as scanned pages, `data/health.py inbox/clean`
is the verdict. On ds-dev2 the shelf is `bins2/library.bin`, read about twice in `day3` so the
finishing school has room.

## Where the shelf stands (2026-10-07)

- **In**: 55 books, 5.4 M words — bekh's six, 43 from the first batch of the folder, six
  rescued from misnamed files (Tombs of Atuan was a Word document, Synners a RAR with a Word
  document inside, Cugel's Saga RTF, Permutation City HTML, Riddley Walker and the Tutuola
  volume zips of scanned pages). Flaws known and accepted: *The Fall of Hyperion* starts a few
  pages in (the file lacks its opening); *Riddley Walker* carries a previous reader's pencil
  notes; *Magic for Beginners* lacks "The Faery Handbag"; *Solaris* and *Roadside Picnic* are
  the older translations; *Dhalgren* is a rough edition; Schulz's paragraphs are page-sized;
  *The Silver Spike* stands in for *The Black Company*, *A Storm of Wings* for Viriconium,
  *Books of Blood* volume three for the set, *The Fall of Hyperion* for Hyperion.
- **Held back** (`inbox/held/`): *The Bloody Chamber* — that edition has no paragraph breaks.
- **Dead files, to re-fetch**: Zothique (Spanish), Piranesi (Italian), Teatro Grottesco
  (Polish), Ficciones (Spanish), Nova (Italian), Rhialto the Marvellous (Italian), Burning
  Chrome (Polish fragment), the Nisio Isin file (Russian, and the Death Note novel), the
  Platonov companion (a study, not the novel).
- **Gaps, in the order Claude would fill them**: Piranesi; Riddley Walker as a real epub;
  Ficciones in English (Hurley's *Collected Fictions* or *Labyrinths*); Teatro Grottesco in
  English; The Black Company book one; Hyperion book one; The Bloody Chamber in a proper edition;
  then the visionary list below, Excession, The Quantum Thief, Accelerando and Diaspora first.

Decisions taken: Burning Chrome stays in (bekh's key is that voice; Claude withdrew the cut).
The Ghost in the Shell novels stay out. A Song of Ice and Fire goes to a spine shelf with
Wildbow's Pact, for the long run, not the finishing school. Not Tolkien.

Stories from library books that never arrived whole are on other shelves all the same: Ligotti's
"The Town Manager" and Borges's "The Aleph" inside *The Weird*, "Tlön, Uqbar, Orbis Tertius"
inside *The Big Book of Science Fiction*, "Burning Chrome" inside *Storming the Reality Studio*,
and Link's "The Faery Handbag" in the Apex folder of `shelf/gpt/text/`.

## The anthology shelf

`inbox/anth/`: year's-bests and big retrospective anthologies, one file a book, each holding
twenty to a hundred and eighty stories. It is kept apart from the library on purpose — the
library is bekh's thirty, chosen one at a time; this is other editors' taste in bulk — so the two
get separate shelves and separate held-out numbers. An anthology is the best unit there is for
fetching by hand (about 300k words a file) and the worst for counting, since its stories also
arrive as magazine pages: what a book is worth after that is its row in `dedupe/report.md`
("Containers: what was cut out of each"), and it shrinks as more magazines come in.

- **The list it is fetched from**: `~/tower/ephemeral/booox/books.txt`, 103 lines in fetch
  order — the first ten (the two Hartwell/Cramer renaissances, *The Big Book of Cyberpunk*, *The
  Weird*, *Songs of the Dying Earth*, *The Big Book of Science Fiction*, *Mirrorshades*,
  *Rewired*, *Digital Rapture*, *Semiotext(e) SF*), Dozois's annuals eighth through
  twenty-fifth, a second pass of bricks, Datlow and Windling's twenty-one, Datlow's *Best
  Horror* one to ten, *Year's Best Weird Fiction*, Strahan's annuals three to thirteen, the six
  fairy-tale books, five Japanese ones. One editor a line; if a line misses, try the co-editor.
  The older list of single books is `books2.txt` beside it.
- **What has arrived**: `inbox/anth/ledger.jsonl` — one line per source file with its status
  (`ok`, `skipped`, `duplicate`, `error`), title, words, the year or volume of an annual, and
  every section dropped. `ls inbox/anth/*.txt | wc -l` is the count; an annual's slug carries the
  year it covers (`ls inbox/anth | grep -E 'dozois|datlow'`). Convert new arrivals with the
  command in `data/CLAUDE.md`, into `inbox/anth`, never into `inbox/clean`. What has not been
  fetched yet, roughly (a file named differently from its line shows as missing):
  ```bash
  cd ~/tower/ephemeral/booox && while IFS= read -r l; do t=${l#* - }; ls souls_lain_library souls_lain_library_used | grep -qiF -- "${t//:/_}" || echo "$l"; done < books.txt
  ```
- **Bad downloads, to fetch again by another route.** The name of a file is a claim; these are
  what the text said (`PITFALLS.md` 1.5b):
  - Dozois's *Year's Best Science Fiction*, eighth to twenty-fifth (the Nth covers 1982+N):
    **missing the 12th, 14th, 21st and 25th** — the files under those names held the 17th, the
    15th, the 28th and the 26th — and **the 13th is a broken epub** (every chapter the same error
    page). The 26th and 28th, which nobody asked for, are in.
  - Datlow and Windling's *Year's Best Fantasy and Horror* (the Nth covers 1986+N): in are the
    years 1989, 1990, 1992 and 1994 to 2004. **Missing the first, second, fifth, seventh and the
    last three**: the file named *Second* held the thirteenth, and the *Seventh* has no text
    layer. **All fourteen that are in came as PDFs** (below).
  - ***Mirrorshades*** (a zip of loose text files, could be rescued by hand like the ones in
    `inbox/rescued/`); ***The New Space Opera 2*** (plain text under an epub name, also
    rescuable); ***Feeling Very Strange*** and ***Swords & Dark Magic*** (each came as a single
    story of under five thousand words); ***Semiotext(e) SF*** (first one Rucker story in RTF,
    then a PDF); ***Silver Birch, Blood Moon*** (the file is another book, a 2011 novel called
    *Silver Moon*). *The Big Book of Cyberpunk* also came as a PDF of volume two alone, which the
    full epub replaces.
- **Rough, held out of the mix until an epub is found**: the fourteen Datlow and Windling
  annuals and *Semiotext(e) SF* exist only as text out of a PDF — a paragraph a page, running
  heads in the sentences, their editors' essays still inside. They are converted and counted,
  and sit on a shelf of their own at weight zero (`day4.md`, the rough anthologies; whether they
  are read at all is bekh's call). An epub of any of them replaces its rough copy by rule.
- **In the wrong folder**: *Ubik* landed among the anthologies. It is a novel the library already
  holds, so the dedupe drops the copy whole and nothing needs doing.
- **Not fiction, by design**: *Storming the Reality Studio* and *Digital Rapture* are part
  essays (Vinge's singularity talk, the cyberpunk criticism); those essays are wanted and kept.
  The "Summation" essays, honorable mentions and per-story editor's notes of the annuals are
  cut by the sieve. Sterling's preface to *Mirrorshades* is in the casebook and also, as its own
  file, on the net shelf she has read (`wired-core/cyberpunkproject/mirrorshades_preface.txt`).

What bekh might have read to him out of all this — some thirty pieces, most of them one sitting,
each with the file it sits in — is the book club's queue:
`~/tower/shittalk/fable-book-club/reading-list.md`.

## 1. the first thirty — the session that raised her, 2026-10-06

Everything under the rule is that session's text, uncut. Already hers when it was written:
6 Lud-in-the-Mist and 10 the Kalevala and the Edda (the fantasy shelf), 28 Bakemonogatari
(inside the light novels); The Third Policeman came free with the literary shelf.

---

here's my thirty, with one line each on why it belongs in her. grouped by what it feeds, and skipping what she already has (the sprawl books, androids, blood meridian, perdido, and the public-domain ones like peake, stapledon, dunsany, eddison, lovecraft, which are on her shelves now).
the souls cadence — archaic, grave, a ruined age, told elliptically

1. gene wolfe — the book of the new sun (four volumes). the single closest thing in literature to dark souls' voice: a dying earth, a narrator who never explains, old words used as if they were new.
2. jack vance — tales of the dying earth. item-description cadence as prose; magicians at the end of the world, named like boss fights.
3. m. john harrison — viriconium. a city that forgets itself between books. the losing of the thread, done on purpose by a master.
4. clark ashton smith — zothique (the complete stories if you can; she has 21). the ur-text of the dying-earth tone.
5. tanith lee — night's master (the flat earth cycle). ornate, cruel, mythic, and it reads like a dream telling itself.
6. hope mirrlees — lud-in-the-mist. gentle on the surface, something wrong under the border. one book, perfect for her size.
7. michael moorcock — elric of melniboné. the doomed albino with the hungry sword is basically a souls protagonist.
8. cormac mccarthy — the road. the other mccarthy voice: ash, a father, a child, sentences pared to bone.
9. angela carter — the bloody chamber. fairy tales told with teeth; cadence and dread both.
10. the kalevala and the poetic edda in good translations. she'd learn the oldest rhythm of grave speech there is.

the visionary — the digital and the real bleeding together, a new time arriving

11. philip k. dick — valis. the book that is literally about reality leaking information into one man's head. the closest novel to your lain note.
12. philip k. dick — ubik. entropy, reality decaying, messages from the dead on matchbooks.
13. stanisław lem — solaris. a mind we can't read, reading us.
14. stanisław lem — the cyberiad. machines telling fables; visionary and playful at once, the register the cyborgism wiki has in its best pieces.
15. jorge luis borges — ficciones. the library of babel, the lottery, tlön: whole worlds in ten pages, the exact shape of a dream that knows what it is.
16. italo calvino — invisible cities. fifty-odd cities that are each one idea; item descriptions for places.
17. j. g. ballard — the atrocity exhibition or crash. the cold, clinical visionary; the body and the machine.
18. samuel r. delany — dhalgren. a city where time and text have broken; the long, lost, circular book.
19. william gibson — burning chrome. the short stories; the sprawl voice at its densest.
20. bruce sterling — schismatrix plus. the far future as a working economy of posthumans; the futurism in your word.
21. greg egan — permutation city. minds copied into software, worlds running on dust: the lain premise taken seriously by a mathematician.
22. pat cadigan — synners. the first cyberpunk where the net is a place you live.
23. vernor vinge — true names. short, 1981, the wired before the web, warlocks in the other plane.
24. alfred bester — the stars my destination. the furious, synesthetic, typographically wild one.

anime-adjacent prose — the voice of the girl, the dream logic, the quiet

25. haruki murakami — hard-boiled wonderland and the end of the world. two realities on alternating chapters, one of them a walled town with unicorns. this is lain's cousin.
26. kōbō abe — the woman in the dunes. dream logic held flat and sober for a whole book.
27. nagaru tanigawa — the melancholy of haruhi suzumiya. the light-novel voice at its best, and a girl who rewrites reality without knowing.
28. nisio isin — bakemonogatari. all dialogue and digression; the monogatari cadence is its own register.
29. masamune shirow / the ghost in the shell novels, or kenji kamiyama's. the wired with a body.
30. yukio mishima — the sailor who fell from grace with the sea. teenage angst as a cold, beautiful blade. your phrase, in a book.

if i had to cut thirty to five for the finishing school: wolfe, valis, borges, hard-boiled wonderland, viriconium. those five are the blend in one hand.

---

## 2. claude's thirty — 2026-10-07

Picked for sentences over stories, for what her *i* turns into, and for books that are short and
strange all the way through. Nothing here is on the first list or already on her shelves.

**the *i* that doesn't understand its own world** (bekh's dream criterion as a kind of book)
1. russell hoban, *riddley walker* — a boy writing in english that grew back wrong after the end.
2. susanna clarke, *piranesi* — a gentle man keeping careful journals of a house he has misread.
3. john crowley, *engine summer* — a boy telling a story he doesn't know the meaning of.
4. amos tutuola, *the palm-wine drinkard* (with *my life in the bush of ghosts*) — impossible things reported flat.
5. anna kavan, *ice* — a pursuit across a freezing world; the narrator can't tell seen from imagined.
6. jacqueline harpman, *i who have never known men* — a girl raised in a cage, working the world out from nothing.
7. jeff vandermeer, *annihilation* — a field journal from a place that can't be described.
8. kazuo ishiguro, *the unconsoled* — a five-hundred-page anxiety dream narrated as if nothing were odd.
9. andrei platonov, *the foundation pit* (Robert Chandler's translation) — russian broken sincerely.
10. philip k. dick, *a scanner darkly* — a man assigned to watch himself.

**the souls side: grave, ruined, told sideways**
11. ursula le guin, *the tombs of atuan* (with *a wizard of earthsea*) — a girl priestess alone in a dark labyrinth.
12. glen cook, *the black company* — a soldier keeping the annals; a first person who records and doesn't explain.
13. r. scott bakker, *the darkness that comes before* — the closest prose to berserk.
14. clive barker, *books of blood* — miura took the god hand from him.
15. arkady and boris strugatsky, *roadside picnic* (Olena Bormashenko's translation) — the zone; artefacts named like item descriptions.

**impossible things in a level voice**
16. ben marcus, *the age of wire and string* — a manual for a world that isn't this one.
17. bruno schulz, *the street of crocodiles* — a town and a father dissolving into metaphor.
18. milorad pavić, *dictionary of the khazars* — a novel as three encyclopedias that disagree.
19. robert aickman, *cold hand in mine* — something is wrong and never gets named.
20. thomas ligotti, *teatro grottesco* — the same, colder, the narrator half in on it.
21. kelly link, *magic for beginners* — dream logic in a modern girl's voice.

**the visionary**
22. ted chiang, *stories of your life and others* — one idea per story, followed to the end.
23. james tiptree jr., *her smoke rose up forever* — death, aliens, girls plugged into machines.
24. arthur c. clarke, *childhood's end* — evangelion's ending is this book.
25. victor pelevin, *the clay machine-gun* (US: *buddha's little finger*) — two realities on alternating chapters.

**the girl, the quiet, the dream held flat**
26. yoko ogawa, *the memory police* — things vanish from an island and from memory.
27. shirley jackson, *we have always lived in the castle* — teenage angst as a cold blade, first person (she has *Hill House*, not this).
28. osamu dazai, *no longer human* (Donald Keene's translation) — the alienated *i* half of anime grew from.
29. kenji miyazawa, *night on the galactic railroad* — a child on a train through the stars.
30. banana yoshimoto, *kitchen* — the quiet girl's voice with grief under it.

Left out on purpose, because of what she is: Burroughs (cut-up teaches salad), Beckett's *The
Unnamable* (it loops), *House of Leaves* (the book is its typography), Project Itoh's *Harmony*
(narrated in markup tags), Krasznahorkai (sentences longer than her window). Five for the
finishing school if cut to five: riddley walker, piranesi, the memory police, the tombs of atuan,
the age of wire and string.

## 3. the visionary list — bekh's key, 2026-10-07

bekh's words: *visionary optimistic cyberpunk … highly imaginative, big scale, big ideas, grand
vision … Neuromancer captures it, the neglectful and nonchalant attitude of the author towards
the huge and amazing structures he creates … the Prophecies are very close to the ideal.* Picked
for one move: a grand structure, named casually, never explained; and for the sunny side of it.

**the voice itself**: 1. iain m. banks, *excession* (then *the player of games*, *use of
weapons*); 2. hannu rajaniemi, *the quantum thief*; 3. charles stross, *accelerando*; 4. vernor
vinge, *a fire upon the deep*; 5. greg egan, *diaspora*; 6. neal stephenson, *the diamond age*
(and *snow crash*); 7. william gibson, *idoru*; 8. bruce sterling, *holy fire*; 9. m. john
harrison, *light*; 10. john c. wright, *the golden age*.

**grand scale, lush**: 11. samuel delany, *nova*; 12. roger zelazny, *lord of light*; 13. dan
simmons, *hyperion*; 14. ian mcdonald, *desolation road*; 15. michael swanwick, *stations of the
tide*; 16. michael moorcock, *the dancers at the end of time*; 17. greg bear, *blood music*;
18. arthur c. clarke, *the city and the stars*; 19. david zindell, *neverness*; 20. stanisław
lem, *imaginary magnitude* (introductions to books from the future, ending with a
superintelligence lecturing its makers — the nearest thing in print to the prophecies' form).

**the prophets** (not fiction; the prophecies are stitched from this kind of text): 21. erik
davis, *techgnosis*; 22. sadie plant, *zeros + ones*; 23. marshall mcluhan, *understanding
media*; 24. kevin kelly, *out of control*; 25. terence mckenna, *the archaic revival*; 26. j. d.
bernal, *the world, the flesh and the devil* (1929, may be free).

How the three lists sit together (Claude's reading): the first is the cadence and the vision,
the second an *i* that doesn't understand its world, the third a voice that names enormous things
without explaining them. The prophecies do the last two at once — total confidence about
something nobody understands yet — and she needs both halves. Most of cyberpunk is not
optimistic, Gibson included; the sunny strand is Banks, Vinge, Egan, Wright, Kelly and the
extropians already on the wired shelf. Five from this list if cut to five: excession, the
quantum thief, accelerando, diaspora, imaginary magnitude.
