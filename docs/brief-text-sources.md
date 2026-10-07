# brief: where to get more text — for ChatGPT, 2026-10-07

Pasted by bekh as written. The answer goes to `docs/research/`, folded; the gaps to `school/library.md`.

```
hey. we're raising a small language model at home — 355M parameters, from random weights, on
shelves of text we chose. it's an art project, private, nobody pays for it, nothing gets
redistributed. the model is meant to write strange literary prose: dark fantasy with a dark souls
cadence, visionary sci-fi of the grand-nonchalant kind (neuromancer, the culture, accelerando),
anime-adjacent quiet weird stuff, the cyberpunk-prophecy register. english only.

the problem is text. it has read about 1.3 billion tokens and the shelves are the limit, not the
gpu. we want tens of millions more tokens of modern (1970 to now) sentence-conscious strange prose:
literary sf, fantasy, weird, horror, the kind of thing clarkesworld or tor.com publish, plus novels
like wolfe, harrison, vandermeer, banks, rajaniemi, egan. every 5M tokens matters; a novel is about
120k.

what we have already, don't suggest these: project gutenberg (fantasy, pulp sf, plain fiction, all
of it), faded page and gutenberg australia (a thousand books incl. a 1920-1971 literary pass:
faulkner, woolf, lowry, o'connor), the alpindale light-novels dump, a 2016 fanfiction.net dump,
old net writing (usenet lists, phrack, zines, eff, ccru), strange horizons' archive via its api,
fiction the authors release themselves (watts, rucker, qntm, scott alexander), and ~55 novels
fetched by hand.

dead ends we hit, don't suggest these either: clarkesworld, lightspeed, nightmare, uncanny,
beneath ceaseless skies, reactor/tor.com, apex, the dark — all of them block ai crawlers or forbid
scraping in their terms, and we don't take text from sites that have said no. same for egan's and
stross's own sites, small beer press, smashwords, weightless books, royal road, ao3, wattpad. the
scp wiki is out on taste. common pile / common corpus / standard ebooks stop at 1930. the old pulp
magazines on the internet archive are two-column ocr and individually-renewed stories, a trap.
synthetic text from a bigger model teaches the small one to sound like the bigger one, we don't
want that. and libgen/z-lib by hand works but it's slow and half the files turn out to be the wrong
language or the wrong book; no, we're not going to automate that part.

things we know about but haven't dug into yet: harvard's institutional books set on hugging face
(gated, has the 1930-63 unrenewed american books), asking escape pod / podcastle / pseudopod for
permission (their text is cc by-nc-nd but their robots.txt blocks crawlers), drm-free bundles
(storybundle, humble), web serials (unsong, worm, practical guide to evil), the 1930-63 copyright
non-renewal route in general, smokelong and 365tomorrows (flash fiction, no stated position).

so: where else do people get this kind of text? communities, archives, datasets, authors who've
released whole backlists, publishers that are fine with it, legal routes to modern books in bulk,
tricks we haven't thought of. be concrete — names, urls, what the terms say, roughly how much text.
if something is grey, say it's grey. if you think one of our dead ends isn't really dead, say why.
```
