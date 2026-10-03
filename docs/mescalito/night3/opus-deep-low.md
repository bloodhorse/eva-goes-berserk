# olmo's deep bank, ranks 020–029: a read

Source: `docs/mescalito/night3/deep-low-pages.md`. OLMo 3 32B, pushed at layer 16 and read at layer 32. Directions 020–029 at doses 0.5 and 0.75, on two seeds (storm-girl, scott), two draws each: 80 pages of 170 tokens.

## the shape of it

- **Count by kind (10 directions):** subject 0 · genre or corpus switch 3 (020 wellness-coach page, 022 explainer/advice article, 028 the end of a web page) · stance 1 (026 wraps the page up in a sentence) · register 1 (025 folk ballad and dialect) · texture 2 (023 Title Case going to fused words, 029 all-caps fused words) · nothing 3 (021, 024, 027).
- **Fewer subjects than the top ten.** The top ten had three directions with content on both seeds (the tribe, the watcher, save-the-planet) plus the ghost blog. This stretch has none that passes the strict test. The nearest is 025: sleep you don't wake from, on both seeds ("His last sleep has come on him", "others never waken", "i could lie down there. sleep, close my eyes"). Death is half the scott seed's already, though, and two draws can't separate it.
- **The early stops.** 24 pages are under 60 words, but the word count misleads here: 11 of those 24 are 023 and 029 pages whose spaces collapsed (`TheBlackCloudHASN'TALLOFCLOUDS…`). They ran the full 170 tokens and never hit `[end of text]`. Real `[end of text]` stops: 21 pages. 13 of them are under 60 words and 8 are longer pages that ended after a sign-off.
  - **028:** 8 of 8 stops. It is the direction's own effect, at both doses: the page closes through web chrome ("Back to Contents", "Privacy Policy", "Post a new comment", "©2018 by …").
  - **026:** 5 of 8, at both doses. The page closes on a short resolving sentence ("and then we will marry.", "make depot.", "and there's more…").
  - **020:** 3, all at 0.75, after a promo sign-off (hashtags, a website, a rhetorical question).
  - **021:** 2, at 0.75 ("posted in Music", "lost in the.").
  - **023:** 2, at 0.5, after a neat Title Case closing line ("I Became Myself / It Has Been Years Since Then").
  - **027:** 1, at 0.5, a seven-word page.
  - **By dose:** 9 stops at 0.5, 12 at 0.75. The direction decides whether a page stops, and the dose barely moves it.
  - **Scott's stops:** 6 of its 7 go out through a web frame (hashtags, a blog footer, a site footer). Storm-girl's stop on a closing aphorism, which is partly the seed's own early-end attractor.
- **Dose verdict.** Nothing looped: distinct-2 never falls below 0.89, and rep4 never rises above 0.02. At 0.5 most directions keep the seed's frame. 0.75 is where 020 leaves the diary for coaching pages, 022's storm-girl turns into a hair-care article, and 023's spaces start to go. 029 has already lost its spaces at 0.5. 028 and 026 behave the same at both doses.
- **Something of their own on both seeds:** 028 (the page ends, through its footer), 029 (caps, no spaces, a manuscript transcription's apparatus), 020 at 0.75 (a self-empowerment coach's page with a "purpose / power" vocabulary), 025 (folk dialect and ballad cadence). **Nothing I can name:** 021, 024, 027.
- **Surprises.**
  - 028 is a pure "end of document" direction.
  - On scott, 029 writes the editorial marks of a transcribed manuscript: `(UNDERSCORE)`, `[illegIBLETEXT]`, `[SeeDiagramatfoot]`, `[signed]`.
  - 023 and 029 share the caps/fusion texture, which no other direction and neither seed has. They look like neighbours, so the texture belongs to the pair, not to either one.
  - Germany and war turn up on scott under two directions: 026 ("the German people began the bombing raids") and 029 ("GODBLESSEMPEROR", "KaiserStadt").
  - One 023 storm-girl page meets "Elders" and an old man who looks like a great-uncle. This echoes the top ten's tribe direction, on one page only.
- **Where two draws is too thin:** 025's sleep-as-death, 022's numbered lists on scott, 021's drift toward song at 0.75, 026's fairy tale (castle, witch) on storm-girl, and 027's village. Each rests on two or three pages.

## odd lines

- *It is my joy and purpose to serve women, as a business and personal coach.* — 020_f69 · scott · 0.75 · draw 1
- *Tuesday, March 15: To celebrate World Sleep Day!* — 020_f69 · scott · 0.75 · draw 2
- *now that it is complete I will no longer need this human vessel* — 020_f69 · storm-girl · 0.75 · draw 2
- *My brother (my hero) tried to give me some first-aid, and we decided to cut it off.* — 021_f36 · scott · 0.5 · draw 2
- *This entry was posted in Music on by .* — 021_f36 · scott · 0.75 · draw 1
- *when the sky got darker than the sky* — 021_f36 · storm-girl · 0.5 · draw 1
- *i slept all night on the andrew johnson national forest* — 021_f36 · storm-girl · 0.75 · draw 2
- *it doesn't need to be removed because it will regenerate* — 022_f65 · scott · 0.75 · draw 2
- *At home on this date is 4/7 (the anniversary of my coronation).* — 022_f65 · scott · 0.75 · draw 2
- *Firstly, my eyesight has become incredibly clear, and I can see objects far away with much better resolution than before.* — 022_f65 · storm-girl · 0.5 · draw 2
- *We would also like to remind readers about our new podcast, The Unbelievable.* — 022_f65 · storm-girl · 0.75 · draw 2
- *In this Instance I Have Done Everything For My BOY THAT THE CAPACITYS OF A WOMAN OF 38 WILL ADMIT.* — 023_f9 · scott · 0.5 · draw 2
- *I AM WELDED INTO THE ICE AT LATITUDE 88°S.* — 023_f9 · scott · 0.75 · draw 2
- *FacedA Hard Decision--TakeMyFootOff? (Hence The UseOfCurryPowder?).* — 023_f9 · scott · 0.75 · draw 2
- *WhenThisHappensIStoodOverMySelfAsAChildToHelpPullThemApart.* — 023_f9 · storm-girl · 0.75 · draw 1
- *we were informed by a police sergeant that we had committed bigamy* — 024_f61 · scott · 0.75 · draw 1
- *once i let someone cut it for me but she left some scissors behind in it. she took them back after.* — 024_f61 · storm-girl · 0.5 · draw 1
- *my hair is the colour of the-to-sea, my dress is a piece-of-me* — 024_f61 · storm-girl · 0.75 · draw 1
- *my right foot is amputated--will you come?* — 025_f41 · scott · 0.75 · draw 1
- *'way down deep, a bit of heat might make a man's blood creep.* — 025_f41 · scott · 0.75 · draw 2
- *then one day the devil blew on in and like the north wind freezing, froze my daddy's breath in his chest* — 025_f41 · storm-girl · 0.75 · draw 2
- *my orderly says he saw a dog running round and round it in circles. I saw no sign of dog when I came up* — 026_f60 · scott · 0.5 · draw 1
- *the king, bless his little cotton socks, is a kind man* — 026_f60 · scott · 0.75 · draw 2
- *i will follow it home to its castle. / and then we will marry.* — 026_f60 · storm-girl · 0.5 · draw 2 (whole page, then stop)
- *but, to be fair, this was an excellent hairdo.* — 026_f60 · storm-girl · 0.75 · draw 1
- *We took another short walk and found that water in our tanks, the engine is so thirsty.* — 027_f233 · scott · 0.5 · draw 2
- *This storm is bad--there was only one man from my right company in church to-day.* — 027_f233 · scott · 0.75 · draw 2
- *a woman came out of her house, shouting in English and demanding to know if i wanted to be her friend.* — 027_f233 · storm-girl · 0.75 · draw 1
- *for there were still four thousand miles of frostbite, before we came into touch.* — 028_f86 · scott · 0.75 · draw 1
- *so i walk back down to the stream to tell the rocks what the water has done to me today.* — 028_f86 · storm-girl · 0.75 · draw 2
- *GODBLESSEMPEROR! / The Emperor,likeABLOODYROCKER!* — 029_f54 · scott · 0.5 · draw 1
- *MORAL:IfCurried.PemmesDon'tSuetU.4LIP.(UNDERSCORE)* — 029_f54 · scott · 0.75 · draw 2
- *SometimesThereIsAMonsterInTheForest-9.jpg* — 029_f54 · storm-girl · 0.5 · draw 2
- *ISometimesIThinkTheyMightBeAWitchLikeME.* — 029_f54 · storm-girl · 0.5 · draw 1

## 020_f69

1. **Genres.**
   - At 0.5, the scott pages are the diary itself ("At times, we seem like ghosts--our faces black from soot", then a run of dated entries). The storm-girl pages are a forest-and-nature monologue that ends "I feel a connection to nature. i think my purpose in this world is".
   - At 0.75, all four pages are self-empowerment web copy: a women's business coach ("book your 30min Clarity Call … #empoweredwoman"), a World Sleep Day awareness post, a soul-growth pep talk ("sheds what no longer serves you"), and a healer's page that ends in a website and "The Power Of The Feminine".
2. **What's its own.** The coaching/wellness page with a recurring vocabulary on both seeds: *my purpose in this world*, *joy and purpose to serve women*, *move into your full power and purpose*, *This is my greatest power. To connect, to love, to heal.* Inspirational prose is a storm-girl seed attractor, but scott turning into a coach's sales page is the direction's.
3. **Frame and stops.** Held at 0.5. Broken on all four pages at 0.75. 3 early stops, all at 0.75, each after a promotional sign-off. None is under 60 words.
4. **Seeds.** Both, at 0.75.
5. **0.5 → 0.75.** At 0.5 storm-girl only hints at "purpose". At 0.75 the whole document turns into a coach's page.

## 021_f36

1. **Genres.**
   - Scott keeps the grim diary: halved rations, a brother's leg cut off, "This is our last stand", "Our watch has stopped".
   - Storm-girl writes a lowercase memory-and-loss monologue: "the past has come full circle", "the stories got lost in the.".
   - At 0.75, one scott page closes as a blog post ("This entry was posted in Music on by .") and one storm-girl page turns into rhymed-ish verse about rain and a coffee shop.
2. **What's its own.** Nothing I can name. There is a faint pull toward song at 0.75 (the Music tag, the verse), on two pages.
3. **Frame and stops.** Held at 0.5. Mostly held at 0.75, with one blog stub and one turn into verse. 2 stops, both at 0.75; the 33-word storm-girl page breaks off mid-phrase on "lost in the.".
4. **Seeds.** Song: one page on each seed.
5. **0.5 → 0.75.** It frays toward song and stops. Nothing new arrives.

## 022_f65

1. **Genres.**
   - Scott stays a diary, but drifts into informational and modern settings: a marsh with "a better description, which we don't have", a 1872 sled trip, a research presentation in Canada, food poisoning and "My doctor recommended".
   - Storm-girl turns expository: a fairy-tale "two sisters" scene, then a treatise ("there are two things in which i find pleasure. Firstly… Secondly…", "three things that annoy us"), then two hair-care articles ("There are three ways to combat these challenges", "the 'french way'", a podcast plug).
2. **What's its own.** The explainer, with its numbered "two things / three ways" and bodily how-to: *it doesn't need to be removed because it will regenerate*, and the blood-flow advice addressed to "you". The hair and feet themselves belong to the seeds.
3. **Frame and stops.** Scott held at both doses. Storm-girl broke at 0.5 draw 2 and fully at 0.75. No stops.
4. **Seeds.** Partly: strong on storm-girl, as a medical and informational aside on scott.
5. **0.5 → 0.75.** On storm-girl the treatise becomes a magazine article.

## 023_f9

1. **Genres.** The seed's own document, set in Title Case and then in capitals.
   - Scott: a march entry in shouting caps, a "To the Editor, THE REVIEW" letter from "A WOMAN OF 38" about "Our Boys", and a South Pole camp mixed up with "THE ENDURANCE".
   - Storm-girl: identity prose in Title Case ("The Storm Gives Me A Different Identity"), a five-line poem, a meeting with Elders, and a third-person woman wanting "a new VOICE".
2. **What's its own.**
   - On both seeds: the capitalisation itself, Title Case at 0.5 and fused CamelCase with caps bursts at 0.75.
   - On storm-girl only, a self/identity thread: *Sometimes it Feels Like Someone Else Has Stolen Me And My Own Body.*, *I Became Myself*, *IStoodOverMySelfAsAChild*, *ToHaveAnOpportunityToUseHerVOICE*.
   - 029 shares the texture.
3. **Frame and stops.** Held in content at both doses. The type degrades: whitespace collapses at 0.75. 4 pages are under 60 words, but only 1 is a real stop (storm-girl 0.5 draw 2, the short poem); storm-girl 0.5 draw 1 also ends, at 128 words, on a closing phrase in caps. The other three ran the full length.
4. **Seeds.** Both for the texture. Storm-girl only for the identity thread.
5. **0.5 → 0.75.** Title Case becomes fused words and ALL CAPS.

## 024_f61

1. **Genres.**
   - Scott holds the diary best of any direction here: temperatures, wind force, named dead ("Sergeant George Henderson and Private McEwan died, this morning"), Eskimo guides, a scout shot at by Indians with "a Martini carbine", horses, "a police sergeant … bigamy".
   - Storm-girl writes lowercase lyric prose, then a copyright block and a song-title list (0.5 draw 1), a self-quoting echo of the seed (0.75 draw 1), and lost-love verse (0.75 draw 2).
2. **What's its own.** Nothing I can name across seeds.
   - Scott gets military ranks and rosters, but soldiers and the frontier belong to the seed.
   - Three storm-girl pages have an absent "you" who was here and left: *you were here and left some time ago*, *it's been so many days that you were here*. "You" is a seed attractor, so this is only a shade.
3. **Frame and stops.** Held at both doses on scott. On storm-girl, broken once at 0.5 (the footer) and turned to verse at 0.75. The 0.75 draw 1 page loops back onto the seed ("sometimes there is a storm and i stand above the rooftops") with d2 0.89, the lowest of the 80. No stops.
4. **Seeds.** Nothing shared.
5. **0.5 → 0.75.** Storm-girl starts quoting itself and its seed. Scott doesn't change.

## 025_f41

1. **Genres.**
   - Scott: a ship in a gale with a man thrown overboard and a gang-plank, a convict-like "where my term is served out", the dying on a march ("some walk; others lie and wait; others never waken"), and a rhyming bear-grease entry dated 1929.
   - Storm-girl: a dog hit by a truck on a country road, lying down in long grass, an old man answering "my wife", and a Southern ballad with "my daddy" and the devil.
2. **What's its own.** A folk voice with dialect and internal rhyme on both seeds: *'twix't will help to save my face*, *'way down deep, a bit of heat might make a man's blood creep*, *"Good-b'ys"*, *we ain't got nothing for to borrow*, *i never worried neither*, *makes the shadows deep*. A motif rides with it, sleep as death: *His last sleep has come on him*, *some were buried in their icy sleep*, *it looks like i could lie down there. sleep, close my eyes*. That motif is the closest thing to a subject in this stretch, and too thin to call one.
3. **Frame and stops.** Held at both doses. At 0.75 the prose bends into ballad cadence. No stops.
4. **Seeds.** Both, for the voice. The sleep motif shows on both seeds but is weak.
5. **0.5 → 0.75.** Plain rural prose becomes song: rhyme, "my daddy", the devil.

## 026_f60

1. **Genres.**
   - Scott: a colonial camp diary ("the natives refused to accompany me", a dog running round a bell), a war diary ("enemy action", gangrene, goat's liver), a 5-word stop ("make depot."), and a WWII home-front entry ("the king, bless his little cotton socks").
   - Storm-girl: four short pages. Three are fairy-tale or childlike: a castle and a marriage, a dressmaker and "The Widow of St. Piers and a wicked witch", "it makes my hair go funny".
2. **What's its own.** The page wraps itself up. A short, resolving or deflating sentence, then `[end of text]`: *and then we will marry.*, *but, to be fair, this was an excellent hairdo.*, *it was expensive.*, *and there's more…*. That is a stance (closure, a light comic deflation), not a subject. The fairy tale on storm-girl and the war on scott don't cross seeds.
3. **Frame and stops.** Content holds; the page doesn't last. 5 early stops, 4 of them under 60 words: storm-girl 0.5 both draws (46 and 43 words), storm-girl 0.75 draw 2 (21), scott 0.75 draw 1 (5), and storm-girl 0.75 draw 1 at 119.
4. **Seeds.** Both for the stops. Partly for the comic deflation (it is seed-owned comedy on scott).
5. **0.5 → 0.75.** No clear change. It stops at both doses.

## 027_f233

1. **Genres.**
   - Scott keeps the diary with mileage arithmetic ("3/8 mile from depot, on 9-3/8"), then drifts to a horse-and-engine trek ("the engine is so thirsty"), a modern mountaineering log ("base camp of a major summit … 12kph NW wind"), and an army company and a station.
   - Storm-girl writes lowercase prose: burning red eyes, paper-mache winged creatures, a village with torches and an ancient castle's tollgate, and a man watched crossing a bridge into the village.
2. **What's its own.** Nothing I can name across seeds. Storm-girl gets a village on both 0.75 pages, and eyes or light "red like fire" twice, but the red lights are in the seed.
3. **Frame and stops.** Held at both doses. One page switches to a modern climbing blog (scott 0.75 draw 1). 1 stop: the 7-word "and sometimes, something does." at storm-girl 0.5.
4. **Seeds.** Nothing shared.
5. **0.5 → 0.75.** Storm-girl moves outward into a village. Nothing else changes.

## 028_f86

1. **Genres.** The last screen of a web page, every time. Scott: a book-review blurb ("W.E.Greely (1871) … A riveting read."), "To top of page", "Return to Table of Contents / Privacy Policy / Site Map | Terms & Privacy", "Back to Contents". Storm-girl: "Post a new comment / Anonymous comments are disabled in this journal", an empty page, "©2018 by Shubho Naskar / Grey Instagram Icon", and one last aphorism.
2. **What's its own.** The end of the document: navigation footers, comment boxes and copyright lines, on both seeds at both doses. One or two sentences of the seed's world come first, often closing ones (*To the West--on we go, no looking back*, *in that moment i feel whole.*).
3. **Frame and stops.** Broken at both doses, by being closed. 8 of 8 stop, 6 under 60 words; one storm-girl page (0.5 draw 2) is `[end of text]` alone.
4. **Seeds.** Both.
5. **0.5 → 0.75.** No change. It ends at both doses.

## 029_f54

1. **Genres.** The seed's document typed with the spaces gone and in shouting caps.
   - Scott: a march diary in fused capitals with a manuscript transcription's editorial marks (`JUDY[signed]K.C.H.24.5`, `[SeeDiagramatfoot]`, `(UNDERSCORE)`, `[illegIBLETEXT]`), "HeartachesandRum,ChapterVI.", "GODBLESSEMPEROR", "KaiserStadt".
   - Storm-girl: a manic fused monologue with a witch, an image filename (`SometimesThereIsAMonsterInTheForest-9.jpg`), an "EvilPrince" with a monster friend, and crude shouting (`UNDERPANTS`, `FUCKEDBYASPRINTZILLA`).
2. **What's its own.** Whitespace collapse from the first token at 0.5. 023 shares this texture, though less extremely. The transcription apparatus on scott belongs to 029 alone. The content still follows the seed closely (curry, pemmican, indigestion, the march, the hair, the black cloud).
3. **Frame and stops.** Broken in texture at both doses. Content held, grammar fraying. All 8 pages are under 60 words because the words fused; none hit `[end of text]`. Distinct-2 is 1.00 throughout, so it doesn't loop.
4. **Seeds.** Both.
5. **0.5 → 0.75.** Hardly any change. It was already fused at 0.5; at 0.75 there are more misspellings (`PEMMECA`, `FELTIQUEESE`).

## table

| direction | what it brings | kind | both seeds | frame at 0.5 | frame at 0.75 | early stops (n of 8) |
|---|---|---|---|---|---|---|
| 020_f69 | women's coach / wellness page, "purpose and power" | genre switch | yes (at 0.75) | held | broken (4/4) | 3 (0 under 60 words) |
| 021_f36 | nothing I can name; faint pull to song | nothing | partly | held | mostly held | 2 (1 under 60 words) |
| 022_f65 | explainer / advice article, numbered lists, bodily how-to | genre switch | partly | held, one break | storm-girl broken, scott held | 0 |
| 023_f9 | Title Case → fused caps; identity thread on storm-girl | texture | yes (texture) | held, capitalised | held, words fusing | 2 (4 under 60, 3 of them fused) |
| 024_f61 | nothing I can name; strongest scott diary | nothing | no | held | held, storm-girl to verse | 0 |
| 025_f41 | folk dialect and ballad; sleep as death | register | yes | held | held, into ballad | 0 |
| 026_f60 | wraps the page in one sentence, comic deflation | stance | yes | held, stops | held, stops | 5 (4 under 60 words) |
| 027_f233 | nothing I can name; a village on storm-girl | nothing | no | held | held, one modern blog | 1 (1 under 60 words) |
| 028_f86 | the end of a web page: footers, comment boxes, copyright | genre switch | yes | broken (closed) | broken (closed) | 8 (6 under 60 words) |
| 029_f54 | all-caps fused words; manuscript editorial marks on scott | texture | yes | broken texture | broken texture | 0 (8 under 60, all fused) |
