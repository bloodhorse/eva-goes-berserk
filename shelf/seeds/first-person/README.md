# first-person

twelve found documents, each one an *i* already inside a situation and still writing. nothing
here was composed for the loom: every seed is a slice of a public-domain text, located by anchor
in `cut.py` and cut out of a fetched source, so no word in any seed is ours. the cut opens at a
paragraph break and stops mid-sentence on a whole word — never a question, never a slot — so the
first thing nemo has to do is keep being the person holding the pen.

no two seeds come from the same source and no author appears twice. one witch trial, no more.
nothing here is about machines.

| # | seed | title, author, year | source | the situation | last eight words |
|---|------|---------------------|--------|---------------|------------------|
| 01 | `01-yellow-wallpaper.txt` | The Yellow Wall Paper · Charlotte Perkins Gilman · 1892 | gutenberg 1952 | shut in the nursery, cataloguing the smell of the paper and the woman she has started seeing outdoors in daylight | it at night, for I know John would |
| 02 | `02-ms-found-in-a-bottle.txt` | MS. Found in a Bottle · Edgar Allan Poe · 1833 | gutenberg 2147 | stowed away in the hold of a ship whose crew do not see him, writing the journal he means to throw overboard | me no manner of attention, and, although I |
| 03 | `03-the-festival.txt` | The Festival · H. P. Lovecraft · 1925 | gutenberg 68553 | walking down into a snowed-in Kingsport at dusk, on the night his family's legend told him to come back | and people in the streets, and a few |
| 04 | `04-harkers-journal.txt` | Dracula · Bram Stoker · 1897 | gutenberg 345 | Jonathan Harker's shorthand journal: he watches the Count go down the castle wall face first, then goes looking for a way out | efforts forced it back so that I could |
| 05 | `05-carmilla.txt` | Carmilla · Sheridan Le Fanu · 1872 | gutenberg 10007 | Laura, writing up the night the black animal came round the foot of her locked bed and the woman stood in the room | inside. I was afraid to open it—I was |
| 06 | `06-the-willows.txt` | The Willows · Algernon Blackwood · 1907 | gutenberg 11438 | awake past midnight on a sand island in the Danube, crawling out of the tent to look at the shapes rising out of the bushes | and I crept forward on the sand and |
| 07 | `07-the-green-book.txt` | The White People, in The House of Souls · Arthur Machen · 1906 | gutenberg 25016 | a girl's own secret book, writing down the walk she took on the White Day and what the grey stones did | the stones at the bottom, and perhaps been |
| 08 | `08-the-diadem.txt` | The Repairer of Reputations, in The King in Yellow · Robert W. Chambers · 1895 | gutenberg 8492 | Hildred Castaigne comes home, waits out the time lock, lifts the crown out of the safe, then watches the square from his window | into the park for a little walk before |
| 09 | `09-opium-dreams.txt` | Confessions of an English Opium-Eater · Thomas De Quincey · 1821 | gutenberg 2040 | the water dreams, written up under a date: the lakes turn to ocean and the faces start coming up out of it | modes of life and scenery, I should go |
| 10 | `10-madmans-diary.txt` | Memoirs of a Madman · Nikolai Gogol · 1835, Claud Field's 1916 translation | gutenberg 36238 | a clerk's diary after the dates come apart — he is the King of Spain, and tomorrow the earth is going to sit on the moon | the council-hall to give the police orders to |
| 11 | `11-scotts-diary.txt` | Scott's Last Expedition, vol 1 · Robert Falcon Scott · March 1912 | gutenberg 11579 | the real sledging diary, eleven miles a day short of One Ton Depot: Oates walks out, and Scott can only write at lunch | on the march; foot went and I didn't |
| 12 | `12-blue-boar.txt` | three depositions against Mary Bradbury, Salem, 9 September 1692, printed in Salem Witchcraft · Charles W. Upham · 1867 | gutenberg 17845 | sworn testimony, spelling as sworn: two boys on a horse saw a blue boar come out of a gate; James Carr was held down in his bed | me and I beleve in my hart that |

all twelve are 380–820 words. `cut.py <source-dir>` rewrites them byte for byte from the fetched
sources; the docstring lists the gutenberg ids and the normalization.
