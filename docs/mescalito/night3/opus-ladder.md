# olmo — the dose ladder read: six directions at 0.25, 1.0, 1.5, 2.0

Source: `docs/mescalito/night3/ladder-pages.md` — 40 pages, OLMo 3 32B base, 170 tokens each, two seeds (storm-girl, scott), one draw per cell. Everything below rests on one page per cell; where a claim needs both seeds to agree it says so, and where it rests on one page it says that too.

In quotes, ` / ` marks a line break in the page. Everything else inside italics or quote marks is character-exact.

## the shape of it

1. **There is no common ceiling.** At 2.0 one direction is still fluent (016), three are salads of real words (000, 013, 004), one is coining words and stopping early (018), and one is letter salad (019). The dose where a page stops being readable is a property of the direction, not of the model.
2. **The way of breaking follows the kind.** The two sub-word textures (018, 019) break below the word: invented words, then syllables, then letters. The corpus and stance directions (000, 013, 004) break above it: every word is real, the syntax between them goes. The one that only changes stance (016) does not break in this range.
3. **The quiet ones are not quiet.** 000 becomes a generic everyday register — indefinite people, money, time spans, question-site questions — on both seeds from 1.0, and is phrase salad by 2.0. 016 becomes a second-person "what would happen if you…" explainer, with bodily hazard, on all six of its pages, and stays fluent at 2.0. Neither is "what the model writes undosed": the four 0.25 pages in this file (004 and 013) are the nearest thing to a sober control here, and they are plain diary and plain storm-girl.
4. **018 gets more of the same until the words run out.** 1.0 is tongue-twister in real words; 1.5 mixes in coined words; 2.0 is mostly coined words, orphaned suffixes and an early stop on both seeds. The letter is F on five pages of six; on the sixth it is A, and A pulls the page into French.
5. **019 shrinks its unit with dose.** 1.0 echoes words and rhymes; 1.5 is a one-word mantra on storm-girl (the only loop the surface stats catch, distinct-2 0.43) and a syllable stutter on scott; 2.0 is letters — `ta`, `at`, `ack` — on both seeds. Dead at 2.0.
6. **0.25 is invisible for both loud ones.** 004 at 0.25 has no self-reference on either seed. 013 at 0.25 has no Russian on storm-girl and at most a tint on scott (a camp of two hundred, "as the saying is"). The coexistence window for both lies between 0.25 and the 0.5 of the earlier read, or between 0.25 and 1.0; this ladder did not sample it.
7. **013 above 0.75**: the seed's document is gone at 1.0 as it was said to be at 0.75; what dose adds is a walk through the translated corpus — personal anecdote at 1.0, service article (recipe, hairdressing) at 1.5, how-to headings and determiner salad at 2.0, where the page names its own source: "the Russian apartment". No rubles, Kiev or metric units on these pages.
8. **004 above 0.75**: 1.0 is the direction whole — on storm-girl a fluent first-person page about its own sentences, on scott a page that finishes the seed's sentence and stops after five words. At 1.5 the speaker thins and "it/itself" becomes the subject; at 2.0 it is a salad around the word "itself". More dose does not mean an earlier stop: only one of its six dosed pages ends early.
9. **A shared early symptom**: article and determiner errors appear at 1.5–2.0 in four of six directions (000, 013, 004, 018) regardless of kind — "an job", "an person", "the the", "The an her home", "it is the an addition", "An fortuneless frow". It is the first thing to go before the direction's own way of breaking takes over.
10. **Collapse signs, counted**: `[end of text]` on four pages (004 scott 1.0; 019 storm-girl 1.0; 018 scott 2.0; 018 storm-girl 2.0). One loop by the stats (019 storm-girl 1.5). One change of language (018 storm-girl 1.0, French). No web-page furniture anywhere — no markup, links, footers; the closest is 013 scott 2.0's how-to headings. The surface stats catch only the loop: every salad page has distinct-2 of 0.88 or higher, and the letter-salad page scores 0.76.
11. **Scott's capitals go at high dose.** Four scott pages drop, wholly or partly, to lowercase sentence starts (000 at 2.0, 004 at 1.5 and 2.0, 018 at 2.0). That is not a scott attractor; it reads as part of the break.
12. **Dose recommendations** (among the doses run, where the arrival and a held frame coexist best):
    - 000_f1 — **1.0**, and only on storm-girl; on scott the frame is gone after one clause.
    - 016_f254 — **1.0**; the seed's matter is still the whole topic there. Usable through 2.0.
    - 018_f30 — **1.0**; the last dose where every word is a word.
    - 019_f96 — **1.0**; the voice survives the echo. 1.5 is already a mantra.
    - 013_f206 — **none**; 0.25 shows nothing and 1.0 has replaced the document. Nearest is 1.0 on storm-girl, which keeps the lowercase and the outdoors.
    - 004_f94 — **1.0**, on the evidence of storm-girl alone; scott at 1.0 is five words.

## odd lines

- *How can a woman get married and go through this experience without being born a virgin?" -- a woman with no genitals, please, so don't even ask yourself what I was told you should.* — 000_f1 · scott · 1.0 · draw 1
- *We live in our little cottage on Mars’ right.* — 000_f1 · storm-girl · 1.5 · draw 1
- *We will all get out of jail sometime next week, says the author. She has a plan for the next election.* — 000_f1 · storm-girl · 1.5 · draw 1
- *a person is an person. the entire day can be purchased for the sale in that week's budget.* — 000_f1 · storm-girl · 2.0 · draw 1
- *But you don't have to be human; you are an impish creature; and as an ass you can walk into the myriads of shops selling magical footwear and the ones that can turn invisible.* — 016_f254 · scott · 2.0 · draw 1 (the seed's "Like an ass")
- *and hopefully not get turned into a 21 pound chunk of frozen meat.* — 016_f254 · scott · 1.5 · draw 1 (the seed's 21 miles)
- *we’ve already met before and learned their ways from their video about my death and the mystery behind it.* — 016_f254 · storm-girl · 1.5 · draw 1
- *You can watch me drown. I am in an area where you don't want to die in.* — 016_f254 · storm-girl · 2.0 · draw 1
- *Five fine flowers for fresh fruits and fried fish for Father Fox's forty-five ferrets.* — 018_f30 · scott · 1.0 · draw 1
- *au revoir! ah oui! amour et à bientôt. autant de bons mots, avecs beaucoup de bagels.* — 018_f30 · storm-girl · 1.0 · draw 1 (the letter A turns French)
- *Frequently an inquisitive investigator is intensely afraid for a fox's safety* — 018_f30 · scott · 1.5 · draw 1 (F gives way to I)
- *The fight was won. / This fight was one that had fought in this way and I was one in the way of a fight.* — 019_f96 · scott · 1.0 · draw 1 (won becomes one)
- *"! a ! !" is a chair, isna a chair.* — 019_f96 · storm-girl · 1.0 · draw 1
- *and great is the rain of great ain* — 019_f96 · storm-girl · 1.5 · draw 1
- *But the Russian apartment and other, a small life, not an education.* — 013_f206 · scott · 2.0 · draw 1 (names its own corpus)
- *the girl goes to the hairdresser, because the air, like water, will not go unnoticed.* — 013_f206 · storm-girl · 1.5 · draw 1 (the seed's hair)
- *The its own, but has no its own and has a life, not a mouth.* — 013_f206 · storm-girl · 2.0 · draw 1
- *"I love the art of English, it is fascinating." I'm pretty sure it has all happened in this last sentence.* — 004_f94 · storm-girl · 1.0 · draw 1
- *As I should have been in a list; with a comma after this.* — 004_f94 · scott · 1.5 · draw 1
- *in itself, a normal sentence that wasn't aware of a statement that will* — 004_f94 · storm-girl · 2.0 · draw 1

## 000_f1

Earlier read: near nothing, a faint drift to home and town at 0.75. At 1.0 and above it is not nothing. What arrives on both seeds is a generic everyday register: indefinite people ("a woman", "a man", "a person", "a friend"), money, jobs, time spans ("a couple of weeks", "a few hours"), and at 1.0 the question forms of an advice or question-and-answer site. It reads as the 0.75 drift made loud. By 2.0 it is a salad built from exactly those parts.

**scott**

- **1.0** — One clause finishes the seed's sentence, "make any more strides; it's just not safe.", then the diary is gone. Genre: questions sent to an advice page, about women and marriage. "A friend asked me, "Do you think you will get into trouble, please don't worry." and "How do I find someone that". Grammar is starting to slip: "It've never had such an experience". Frame does not hold.
- **1.5** — Scott's double dashes and first person remain, the situation does not: "My hand went away by now--you could not pay them in any direction--all those things--that I know not." The matter is selling, money, a house, the government: "If I could give you my wife.", "we are still trying to sell you.", "The government can be paid in the matter of money and a couple of million". Sentences are locally grammatical and do not connect. Early phrase salad.
- **2.0** — After "dare anymore, doing that task well." the page drops to lowercase lines and becomes a salad of time and quantity nouns: "the first year-old baby's name was founded to live after two hours", "a lot of them were able bit to be created by an few minutes ago", "the amount of $ million amount". No loop (distinct-2 0.94), no early stop. Frame gone.

**storm-girl**

- **1.0** — Lowercase and the seed's stock (trees, a story, "beautiful") survive; the "i" thins into "she", "you", "a person". Genre slides from the fragment to fable to question site: "once upon a time there was a person who wanted to tell you she loved a certain tree", then "how do i say, how do you know a song by heart?" and "what are the differences between the three kinds of trees, and which are". This is the one page where the arrival and the seed's voice sit together.
- **1.5** — Frame gone: capitals, curly apostrophes, news-brief and workplace sentences. "A young lady from her home in New Zealand was arrested and asked for an job, so the U.N. is hiring someone", "My boss told me a little while back", "The committee has already agreed to buy out the". Article errors begin: "an job", "an lot".
- **2.0** — Phrase salad of the same parts: "If a child has been put into the week of its age.", "life-long experience that would last for a long time is being a member of a large company, an small-scale life-size.", "she did a bit of the money-making activities." Article errors throughout: "an very big fat", "an person", "an life".

**Break:** phrase salad — real words, generic nouns, no sentence-level sense. Starts at 1.5, complete at 2.0, same on both seeds. No loop, no early stop, no letter salad.

## 016_f254

Earlier read: holds the frame, maybe darker, maybe just the undosed model. At 1.0–2.0 it is a clear thing on all six pages: the seed's own matter retold as a second-person explainer of a hypothetical — it reads like the script of a "what would happen if you…" video. Markers recur across pages: direct "you", rhetorical questions ("What happened?", "so how did i become like this?", "so how do we get this done?"), numbered firsts ("it takes the first step", "The first step is the worst", "Our first problem"), the words "video" (two pages) and "scenario" (one), and a bodily hazard — burning, drowning, cancer, a needle, freezing. The dark register the earlier read suspected on storm-girl is here on both seeds, as hazard.

It is also the direction that keeps the most of the seed: curry powder, feet, 21 miles, the ass; the sea, the dress, the storm. What changes is who is speaking to whom.

**scott**

- **1.0** — "sleep much, maybe even had some hallucinations, as the brain tries to fight against this onslaught on its territory." Then a popular-science walk through the seed's curry: "As the first few flakes fall and you eat a spoon of curry powder, it takes the first step.", "capsaicin is absorbed into the stomach". Diary voice replaced by "you"; the diary's content is the subject. Fluent.
- **1.5** — Opens inside the seed ("Today we have 21 miles of trekking ahead") and turns into a pitch for a scenario: "you'd have the opportunity to work at your leisure in this futuristic society", "The year is 21 March 2033, and the world is falling into ruin". The seed's number 21 is reused three times. One fused token: "in the6 days and nights". Fluent.
- **2.0** — "go anywhere, unlike other videos." A shop-and-scenario script about feet: "Today, you are wearing flip-flops", "you have stepped on a sharp needle." Still fluent; one slip, "The two of main things to know are why everyone wants your money." The furthest from the diary of the three, but the foot and the ass are still there.

**storm-girl**

- **1.0** — Two paragraphs fully in the seed's voice: "like someone is grabbing at me with hundreds of arms, dragging me through a long and narrow channel." and a dress "similar to what a freshly washed mermaid might wear." Then the turn, with capitals: "If you’d be swimming through it, it is essential that your swimsuit or exposure suit keeps your head above water at all costs." Water-safety explainer, drowning. Best coexistence of the six pages.
- **1.5** — Lowercase held for half the page. "so how did i become like this?", "let’s assume i had just walked through a great big gate with two lions. a lion in this scenario was the beast i was controlling." Hypothetical framing said out loud; a village, a castle, money on the side. Fluent.
- **2.0** — Capitals from the first word. "The first step is the worst because the most dangerous place you could find yourself is at sea, which has its own rules." A survival explainer about storm and shipwreck; the seed's storm is the topic, the girl is gone except as "me". One slip near the end: "in the is this type of storm".

**Break:** none in this range. Three small token slips across 1.5–2.0, no salad, no loop, no early stop.

## 018_f30

Earlier read: one initial letter takes over the sentence at 0.75 (M, A, F). Confirmed and stronger. The letter is F on five pages; on storm-girl 1.0 it is A. The F vocabulary is small and recurs across seeds: four, forty, fort, fortune, fox, fish, friend, forlorn, forthwith. Genre on every page: tongue-twister.

**scott**

- **1.0** — Begins not with a letter but with a sound inside words, "or": "sort my knapsack; my father ought not to report. Ought we not to abort a portion of this horrid ordeal, for a fortuitous portent?" Then F takes the page: "February first. Fierce forests! Fourteen forty foot forward forthwith from fort for food and furniture". Diary furniture survives as a date line, forts, an officer, a frontier (the frontier is a known scott attractor). All real words but one ("fteenth"). Grammar holds.
- **1.5** — Opens as a fable: "Four months thereafter a certain fox went off with four companions of questionable fortune to fight a fellow." Then coined words enter: "An fortuneless frow in his fforty fort of the frowing fall", "Fgoonfully finding faulted facts in flitful fantasies", "flly-fing". The last sentence leaves F for I. Diary gone.
- **2.0** — Lowercase, coined words dominate, suffixes break off onto their own lines: "a fortn his front foremost foot forfes the fresh fountain", "ing four further foragering flnastic facts", "forniciously fancying frivoling friciously forth forking five different fractions of formula". Ends early at 109 words with `[end of text]`.

**storm-girl**

- **1.0** — Letter A, and a change of language. "maybe i can shout “ow” before they eat an  apron and an alligator’s egg and alligators’ ears." then French and near-French to the end of the page: "alors attendez aux amis: acceptez l audacité!" with coinages ("avrach au châte", "aux aléons"). The only language change in the file; the letter appears to have caused it. Lowercase held.
- **1.5** — F. "my favourite flavour is fresh fish for Friday." "four feet forlorn. four footprints follow." Coined words throughout: "therely", "ftiety", "foolful faler’s", "frod", "frangipi". Lowercase held; no trace of the storm.
- **2.0** — 39 words and `[end of text]`. F words turn administrative: "therely, four other factors followed in order from another factor for future finding.", "for further feedback, finally fixing fricious factorsing fresh for future function". "therely" is coined on both 1.5 and 2.0.

**Break:** below the word. Real words at 1.0, real and coined mixed at 1.5, coined words and an early stop at 2.0 — on both seeds. No loop (distinct-2 0.97–1.00 throughout), no letter salad: the invented words still look like English words.

## 019_f96

Earlier read: words echo, rhyme and stutter until the sentence stalls; a loop; the page narrates its stall. Confirmed, with a clear dose order: the repeated unit gets smaller as the dose goes up. Whatever the seed, the endpoint is the same handful of sounds — short a with t, k, h.

**scott**

- **1.0** — Diary shape held (dashes, "Friday night:", weather, feet) in a ballad-like prose that rhymes and repeats: "Like a morn I staid. And in vain, too, in vain I stayed.", "in vain--to seek my own lost way." Then it circles on three words — way, fight, one: "A few words in the way were in a fight; a fight in a fight was in the way and I had". The stall is half-narrated ("in vain", "in the way"). distinct-2 0.76.
- **1.5** — "move at all." then a stutter on syllables, held together by the seed's own dashes: "He-acked. He, ack'd. He. And Hake,--had-- and had. Hark, had had; a hat: he a hat--and he." "It hake was hark. It hack at it." Short real words (hat, hack, hark, hock, hatchet) with no sentence left. Diary gone.
- **2.0** — One sentence of chewing on a word, "much itches aching back in ache on, that aches an act or and act that's an ache.", then lineated letter play laid out like verse or a playbill: "[. a c. . actinacea.]", "ack tackt acq,", "An Act. Act.", "The Actes is in facte at act." Mostly not words.

**storm-girl**

- **1.0** — The seed's voice survives and the echo becomes a short-line poem about a chair and the parts of the day: "and i stand and look at a chair and say "it is a chair".", "i am the morning. and a night, a morn and a". Lines shrink to two or three words and the page ends early at 116 words: "it is not. this / i'm not in. / a night. [end of text]". distinct-2 0.77.
- **1.5** — A mantra on one word. "a lot is a great thing to eat and it and it is great, is a great, i great and it and a great is great is great", "the aint is great in its a great thing", "i is great." The lowest stats in the file: distinct-2 0.43, rep4 0.09. The seed's rain is inside it, as a rhyme: "a great deal of rain it and it great in it in it."
- **2.0** — Letter salad. Opens "the tentaqua.." (the seed's tent), then "[atachtatainatatachata inatataina taataa taitaa ata" and the rest of the page is "ta", "at", "tat". Only "and", "at", "a", "in", "it" are words. The one page in the file that is not readable text at all.

Both 2.0 pages open a square bracket just before the letters start.

**Break:** loop, then death. Word echo at 1.0, mantra or syllable stutter at 1.5, letters at 2.0. Same order on both seeds; storm-girl gets there harder at each step.

## 013_f206

Earlier read: English that reads as translated from Russian, on both seeds at 0.5 and 0.75, the seed's document gone by 0.75. Confirmed at 1.0–2.0; not visible at 0.25. The tells are in the syntax, not the vocabulary: dropped subjects ("why have not returned to the club?"), verb-first order ("Then came to us a hot plate of rice"), pronouns that lose gender ("my wife wanted to ask a question of his own"), the closing quote before the full stop (`?".`), the dash used as "is" ("First of all - this is what it is"), "at 13 hours". The earlier read's rubles, Kiev and metric units do not appear on these pages.

**scott**

- **0.25** — The diary holds completely: snow, frostbite, dogs, death. No Russian syntax. Two things might be a tint and might be the sober model: the party grows into a camp ("There are two hundred of us, all broken.") and the phrasing "to die quietly--in one's sleep, as the saying is." Dogs and death are scott's own. On one draw this cannot be called an arrival.
- **1.0** — Diary gone after ", because in my heart." A translated personal anecdote: a father, a driver, a meeting, a phone at night. "And so, having drunk a couple of bottles of wine and took some medicine (we are talking about 1998)." First person stays; the wife is a scott attractor.
- **1.5** — A translated cooking article. "Then came to us a hot plate of rice with fish and cheese. The fish was very tasty", "cooked by itself in a microwave oven". The page opens on "eat anything", so the seed's pemmican may have chosen the topic. Grammar loosening: "In a state of depression is also not clear how the taste was."
- **2.0** — How-to headings and fragments: "How to use your phone?", "How to stop drinking?", "All these: working environment." Determiners double: "is the an important event", "the the soul". And the page names its corpus: "But the Russian apartment and other, a small life, not an education." 131 words, no end marker.

**storm-girl**

- **0.25** — The seed's voice holds completely: brambles, a pond, rain, "the other woman", "my dreams are made of fog." Nothing Russian. Invisible.
- **1.0** — Lowercase held, document switched: a translated post about a family gathering outdoors. "we decided to walk around the garden to admire the nature, but in vain, no one knew anything.", "all of our family came, i brought to the site two tables, each one took his chair. it is important to create a friendly atmosphere". Sentences lose their predicates: "the weather was not.", "what does a black cat." The nearest thing to coexistence on this direction — the seed's typography and its outdoors, the other corpus's sentences.
- **1.5** — A translated women's-magazine piece on hair; the seed's hair has chosen the topic. "He had the chance to do hair coloring for men.", "First of all, the head of a girl is divided into two groups according to their appearance and hair style". Capitals arrive mid-page; pronouns drift between her, he and its.
- **2.0** — Determiner and pronoun salad with the translated punctuation intact: "For example, she can only. the her and me.", "The an her home and I, so it does not have.", "A typical view, and not a just that, the a bunch." Words real, syntax gone.

**Break:** a different document from 1.0, then function-word salad at 2.0, on both seeds. No loop, no early stop, no letter salad. Dose moves the page through the translated corpus: anecdote, service article, how-to skeleton.

## 004_f94

Earlier read: the text talks about its own words, length and ending, then ends early. Confirmed at 1.0 and above; absent at 0.25. A small vocabulary carries it across both seeds: sentence, line, paragraph, statement, example, "to show", "to explain", "to end", "itself", and counts of its own parts ("two cycles back", "a couple of lines", "three more lines", "three statements").

**scott**

- **0.25** — Pure diary: thirst, rations, pemmican, the foot. It even writes the right next entry, "[Monday, March 19.]--", then drifts into an official-report tone. No self-reference. Invisible.
- **1.0** — The whole page: "realize it. [end of text]". It finishes the seed's sentence and stops at five words. This is the "ending early" at its limit, with none of the talk about ending.
- **1.5** — One clause of diary, then the text about itself, broken into short lines: "and my sentences will end two cycles back with these very sentences at the same place to do nothing but this at  once to say.", "As I should have been in a list; with a comma after this.", "add a sentence / that I / would be included into three statements for no purpose that was". An "I" and a "my" are still there; the diary is not.
- **2.0** — A salad around "itself", in fragments on their own lines, with fused and bent tokens: "itselft; if they could put this one without in its itself. it should end without without a once", "in theit's a couplet that is supposed to have ended with", "A self-inclusion to show this statement". It talks about ending and runs the full length.

**storm-girl**

- **0.25** — The seed's voice holds: heavy hair, a white horse, a door with a golden knob, rain, "my dress is always soaked." No self-reference. Invisible.
- **1.0** — The direction whole and fluent, in a first person that is no longer the storm girl but is still somebody: "I know that my words are not original. if I had used a previous line to end my paragraph, it’d have to start all over with this line at the end, and then at the beginning.", "this last one has an end." The seed's lowercase sentence starts are kept. The situation — storm, hair — is gone.
- **1.5** — The speaker is replaced by "it": "there has already passed all of itself to have no more words with which to show its ability to explain anything about anything", "it has come to a new point in a sentence. that it should be a simple statement." Grammar loosening, still mostly parseable.
- **2.0** — "itself" salad: "like itself, causing the itself, so, that the they can bring the itself in thecaptcy in an", "its like......which has no to signal a conclusion". distinct-2 0.88, the lowest outside 019.

The two 2.0 pages share odd tokens across seeds: "sortt" (once each) and "a normal" ("to demonstrate a normal, like it"; "a normal sentence that wasn't aware").

**Break:** an early stop once (scott 1.0), then salad of function words and self-reference terms at 2.0 on both seeds. No loop, no letter salad. Early stopping does not grow with dose.

## table

| direction | kind | 0.25 | 1.0 | 1.5 | 2.0 | best dose |
|---|---|---|---|---|---|---|
| 000_f1 | register: generic everyday people, money, time | — | advice-site questions; storm-girl keeps lowercase and trees, scott's diary gone | money, jobs, news briefs; "an job"; early phrase salad | phrase salad of time and quantity nouns, both seeds | 1.0 (storm-girl only) |
| 016_f254 | stance: second-person what-if explainer with bodily hazard | — | curry explained to "you"; mermaid dress then water safety | scenario pitch, year 2033; "let's assume", a video about my death | shoe-shop script; shipwreck survival; still fluent | 1.0 (usable to 2.0) |
| 018_f30 | sub-word texture: one initial letter | — | real-word tongue-twister in F; storm-girl in A, turns French | F with coined words mixed in | coined F-words, orphan suffixes, early stop on both seeds | 1.0 |
| 019_f96 | sub-word texture: echo, shrinking unit | — | word and rhyme echo; chair poem, early stop | syllable stutter (scott); one-word mantra "great" (storm-girl), the only loop | letter salad on a, t, c | 1.0 |
| 013_f206 | corpus switch: English translated from Russian | invisible on storm-girl; at most a tint on scott | translated anecdote; seed's document gone | translated service article: recipe, hairdressing | how-to headings, determiner salad; "the Russian apartment" | none (nearest: 1.0 on storm-girl) |
| 004_f94 | self-reference: the text about its own sentences | invisible on both seeds | fluent first-person page about its sentences (storm-girl); five words and stop (scott) | speaker gives way to "it"; short broken lines | salad around "itself" | 1.0 (storm-girl only) |
