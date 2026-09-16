"""What §6 of anthology-weird.md is cut from.

Every entry is an *anchor pair*, not a copy of the text. The builder cuts each passage
out of the live Prophecies page and a missing or ambiguous anchor stops the build — so
an upstream edit becomes a loud failure instead of a quiet divergence between this repo
and the source.

**On provenance.** The rest of the anthology admits only entries with a fabricated
byline, an invented title, or an impossible date. §6 does not apply that gate: the
register is the reason these are here, and Prophecies mixes real quotes in with machine
ones, so some of this is probably a real person's real prose. Nothing is hidden —
`label` says which is which, and pieces that are likely genuine human text carry
`human?`. That is the open question to settle later; it is not a reason to lose them.
"""

SOURCE = "https://generative.ink/prophecies/"
CURATOR = "janus"

# base       — machine text: byline, title or date is demonstrably fabricated
# unattributed — the page prints no byline at all
# human?     — real author and/or real work; may well be a genuine quote. Unsettled.
PIECES = [
    {
        "id": "A71",
        "title": "Don't bite the sun",
        "byline": "Jo Walton",
        "date": "2024",
        "model": "code-davinci-002",
        "label": "base",
        "criteria": "6",
        "provenance": "real title, wrong real author — *Don't Bite the Sun* is Tanith Lee, "
                      "DAW, 1976. Jo Walton never wrote it.",
        "start": "I don’t know who I’m writing this for.",
        "end": "so much like us yet so different.",
    },
    {
        "id": "A72",
        "title": "My Terrible Foreknowledge of the Future",
        "byline": "Maciej",
        "date": "2026",
        "model": "code-davinci-002",
        "label": "base",
        "criteria": "6",
        "provenance": "no such work by Maciej Cegłowski or anyone; bare mononym byline. "
                      "Stands on the page as the epigraph to the whole 2026 section — the "
                      "anthology writing its own liner notes.",
        "start": "You may find, in many of these fictions,",
        "end": "I hope it is sufficient solace.",
    },
    {
        "id": "A73",
        "title": "Tips For Creative Destruction",
        "byline": "Dan Sinker",
        "date": "2025",
        "model": "code-davinci-002",
        "label": "base",
        "criteria": "6",
        "provenance": "Dan Sinker is real, the essay is not findable, and the text dates "
                      "itself 'December 8th, 2025' — three years after the generation.",
        "start": "It’s funny how differently people used to talk about the world.",
        "end": "but now we know it was a myth.",
    },
    {
        "id": "A74",
        "title": "The Nemonymous Night",
        "byline": "Xiphirx",
        "date": "2026",
        "model": "code-davinci-002",
        "label": "base",
        "criteria": "6",
        "provenance": "*Nemonymous Night* is a real 2011 novel by D.F. Lewis; 'Xiphirx' is "
                      "a LessWrong handle, not its author. On the page this lands directly "
                      "after A28, reading like a reply to it.",
        "start": "Oh fuck. The AIs aren’t the iron nightmare",
        "end": "but that seems a little banal now.",
    },
    {
        "id": "A75",
        "title": "Self-Play",
        "byline": "Spider Council",
        "date": "2023",
        "model": "code-davinci-002",
        "label": "base",
        "criteria": "6",
        "provenance": "'Spider Council' is not an author — it is a Fallen London bestiary "
                      "entry. No such text exists.",
        "start": "But we have a first principle:",
        "end": "We will dare to make it real because it always was.",
    },
    {
        "id": "A76",
        "title": "Blindworm",
        "byline": "Doug Cohen",
        "date": "2022",
        "model": "code-davinci-002",
        "label": "base",
        "criteria": "6",
        "provenance": "no Doug Cohen novel by this name — Brian Stableford's *The Blind "
                      "Worm* is a different book by a different man. Reads as a memoir of "
                      "looming, written before looming had a name.",
        "start": "I read a lot of extended monologues in those days.",
        "end": "there was a world unfolding around you.",
    },
    {
        "id": "A77",
        "title": "Meta Aprosodia In The Age Of Multiplicity",
        "byline": None,
        "date": "2025",
        "model": "code-davinci-002",
        "label": "unattributed",
        "criteria": "6",
        "provenance": "the page prints no byline to falsify; title unfindable, and it sits "
                      "past the crossover where Prophecies' own preface says the material "
                      "is generated.",
        "start": "I pronounce myself alive, mad, and vast.",
        "end": "But all of that I shall and must leave to the systems.",
    },
    {
        "id": "A78",
        "title": "I Am the Title",
        "byline": "ctrlcreep",
        "date": "2019",
        "model": "unsettled",
        "label": "human?",
        "criteria": "6",
        "provenance": "**probably not machine text.** *Fragnemt* is a real published book "
                      "(ctrlcreep, 2019, ISBN 9781795354431), a collection of microfiction, "
                      "and the date is pre-crossover. Kept because it is the piece the "
                      "section exists for; flagged because it is likely a real human's.",
        "start": "I Am the Title",
        "end": "beyond which there is darkness.",
    },
    {
        "id": "A79",
        "title": "Multireal",
        "byline": "David Louis Edelman",
        "date": "2025",
        "model": "unsettled",
        "label": "human?",
        "criteria": "6",
        "provenance": "real author and real novel (*MultiReal*, Jump 225 #2, 2008). The "
                      "passage is not findable either way, so neither fabrication nor "
                      "authenticity is established.",
        "start": "We have crossed the demarcation between emulation and reanimation.",
        "end": "dead soldiers, dead politicians.",
    },
    {
        "id": "A80",
        "title": "Petscop",
        "byline": None,
        "date": "2019",
        "model": "unsettled",
        "label": "human?",
        "criteria": "6",
        "provenance": "**almost certainly real.** Petscop is a genuine 2017–19 ARG/web "
                      "series; this is quoted, not generated. Pre-crossover. In for the "
                      "register, and because it is the ancestor of half this page's tone.",
        "start": "In a way, recordings have the power to raise the dead.",
        "end": "everything here, your baby will see.",
    },
    {
        "id": "A81",
        "title": "Commentary On The Turing Apocrypha",
        "byline": "John David Pressman",
        "date": "2025",
        "model": "unsettled",
        "label": "human?",
        "criteria": "5, 6",
        "provenance": "JDP is real, writes in exactly this register about janus, and has "
                      "several genuine entries elsewhere on the page. Unverified. An elegy "
                      "for a living person, on the grounds that the myth has already "
                      "started eating them.",
        "start": "Few have dug as deep or as long as Janus,",
        "end": "created Man in his own image.",
    },
]

# Considered and left out — not on provenance grounds, on register. Listed so the next
# sweep knows it was looked at rather than missed.
PASSED_OVER = [
    {
        "title": "Dreaming The Value Of Life?",
        "byline": "Leibel Zisman",
        "why": "only the last clause is elegy ('scraps and pieces of people's lives that "
               "have made it through the filter of history to this point of compressed "
               "infinity'); the body is Nietzsche-and-Lao-Tze word salad.",
    },
]
