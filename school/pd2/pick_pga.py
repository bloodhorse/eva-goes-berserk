import re, sys
sys.path.insert(0, ".")
import uspg

F, S = "fantasy", "scifi"

AUTH = {
    "Howard, Robert Ervin": F, "Machen, Arthur": F, "Merritt, Abraham": F, "Williams, Charles": F,
    "Bouve, Edward Tracy": F, "Stevens, Francis": F, "Haggard, Henry Rider": F, "Nesbit, Edith": F,
    "O'Brien, Fitz-James": F, "Shiel, Matt P.": F, "Hodgson, William Hope": F, "Blackwood, Algernon": F,
    "James, M. R. (Montague Rhodes)": F, "Lindsay, David": F, "Lovecraft, Howard Phillips": F,
    "Morris, William": F, "Benson, Edward Frederick": F, "Hoffmann, Ernst Theodor Amadeus": F,
    "Tieck, Johann Ludwig": F, "Gautier, Theophile": F, "Harvey, William Fryer": F, "Malden, Richard Henry": F,
    "Swain, Edmund Grill": F, "Gray, Arthur": F, "Walpole, Hugh": F, "Cram, Ralph Adams": F,
    "Chambers, Robert W.": F, "Crawford, F. Marion (Francis Marion)": F, "Capes, Bernard (Bernard Edward Joseph)": F,
    "Heron, E. and Heron, H.": F, "Level, Maurice": F, "O'Sullivan, Vincent": F, "Stenbock, Eric": F,
    "Ewers, Hans Heinz": F, "MacCreagh, Gordon": F, "Vivian, E. Charles": F, "Eddison, Eric Rucker": F,
    "Nisbet, Hume": F, "Praed, Rosa": F, "Allen, Grant (Charles Bainbridge)": F, "Clarke, Marcus": F,
    "Gaskell, Elizabeth Cleghorn": F, "Lewis, M. G. (Matthew Gregory)": F, "Baring-Gould, S. (Sabine)": F,
    "Benson, Arthur Christopher": F, "Brodie-Innes, J.W.": F, "Craig, Randall": F, "Shelley, Percy Bysshe": F,
    "Stockton, Frank R.": F, "Straus, Ralph": F, "Warren, Samuel": F, "Watson, Henry Brereton Marriott": F,
    "Shelley, Mary Wollstonecraft": F, "Scott, G. Firth": F, "O'Brien, David Wright": F, "Buchan, John": F,
    "Doyle, Arthur Conan": F, "Sabatini, Rafael": F, "Mulholland, Rosa": F, "Northcote, Amyas": F,
    "Oliphant, Margaret": F, "Riddell, Charlotte": F, "Molesworth, Mary Louisa": F, "Broughton, Rhoda": F,
    "Braddon, M. E. (Mary Elizabeth)": F, "Baldwin, Louisa": F, "Croker, B. M. (Bithia Mary)": F,
    "Wintle, W. James": F, "Edwards, Amelia Ann Blanford": F, "Freeman, Mary Eleanor Wilkins": F,
    "Hogg, James": F, "Abdullah, Achmed": F, "Morrow, William Chambers": F, "Marryatt, Frederick": F,
    "Hearn, Lafcadio": F, "Sinclair, May": F, "Stoker, Bram": F, "Lippard, George": F, "Gilchrist, Robert Murray": F,
    "Platt, James": F, "Prest, Thomas Peckett": F, "Schwob, Marcel": F, "Storm, Theodor": F, "Neruda, Jan": F,
    "Roman, Victor": F, "White, Edward Lucas": F, "Askew": F, "Alice and Claude Askew": F, "Heron-Maxwell, Beatrice": F,
    "Le Fanu, J. Sheridan": F, "Maturin, Charles": F, "Parsons, Eliza": F, "Sleath, Eleanor": F, "Lathom, Francis": F,
    "Ludlow, Fitz Hugh": F, "Mayne, Ethel Colburn": F, "Douglas, George Norman": F, "Anonymous": F,
    "MacDonald, George": F, "Villiers de l'Isle-Adam, Auguste": F, "Pigault-Lebrun, Charles Antoine Guillaume": F,
    "Field, Eugene": F, "Hare, Augustus": F, "Hartman, Franz": F, "Cholmondelay, Mary": F, "Colton, Arthur Willis": F,
    "Gogol, Nikolai": F, "Quiroga, Horacio": F, "Maupassant, Guy de": F, "Simpson, Helen de Guerry": S,
    "Stapledon, Olaf": S, "Weinbaum, Stanley G.": S, "Griffith, George": S, "Kline, Otis Adelbert": S,
    "Jameson, Malcolm": S, "Wells, Herbert George": S, "Bryusov, Valeri": S, "Mitchell, Edward Page": S,
    "Nowlan, Philip Francis": S, "Cox, Erle": S, "Zagat, Arthur Leo": S, "Giesy, John Ulrich": S,
    "Von Harbou, Thea": S, "Walsh, James Morgan": S, "Morrow, Lowell Howard": S, "Spence, Catherine Helen": S,
    "Pollack, Frank L.": S, "Breuer, Miles J.": S, "Anthony, Wilder": S, "Curtis, Wardon Allan": S,
    "Spofford, Harriet Prescott": S, "Grove, Frederick Philip": S, "Verne, Jules": S, "Capek, Karel": S,
    "Orwell, George": S, "Hilton, James": S, "Leacock, Stephen": S, "Wallace, Edgar": S, "Orton, J. R.": S,
    "Fletcher, Joseph Smith": S,
}

TITLE_SHELF = {
    ("Doyle, Arthur Conan", r"Challenger|Maracot"): S,
    ("Wells, Herbert George", r"Croquet|Pearl of Love"): F,
    ("Stevens, Francis", r"Cerberus"): S,
    ("Lindsay, David", r"."): F,
}

KEEP = {
    "Doyle, Arthur Conan": r"Challenger|Twilight and the Unseen|Maracot|Brown Hand|Playing with Fire|Holocaust",
    "Buchan, John": r"Witch Wood|Supernatural|Gap in the Curtain|Far Islands|Runagates|Dancing Floor",
    "Wallace, Edgar": r"Planetoid",
    "Leacock, Stephen": r"Asbestos",
    "Fletcher, Joseph Smith": r"New Sun|Other Sense",
    "Sabatini, Rafael": r"Spiritualist",
    "Lewis, M. G. (Matthew Gregory)": r"Anaconda|Mistrust",
    "Lovecraft, Howard Phillips": r"Collected",
    "Shelley, Mary Wollstonecraft": r"Mortal|Dream|Evil Eye|Invisible|Ghosts",
    "Merritt, Abraham": r"^(?!Seven Footprints)",
    "Haggard, Henry Rider": r"Heu|Treasure|Ice Gods|Wisdom|Belshazzar",
    "Howard, Robert Ervin": r"^(Conan|Solomon|Kull|Bran|Cormac|Conrad|De Montour|Turlogh|James Allison|Red Sonya|Fantasy|Historical|Horror|Weird|Cthulhu|Faring|Almuric)",
}

INDEX_EXTRA = [
    (F, "Howard, Robert Ervin", r"^(The God in the Bowl|The Black Stranger|The Garden of Fear|Dig Me No Grave|Black Hound of Death|Old Garfield's Heart|The Dead Remember|Cimmeria - A Poem|The King and the Oak  A Poem|The Challenge from Beyond|Red Blades of Black Cathay|The Man on the Ground)$", r"Robert (E|Ervin) Howard"),
    (F, "Morris, Kenneth", r"Regent of the North", r"Kenneth Morris"),
    (F, "Dahn, Felix", r"Halfred", r"Felix Dahn"),
    (F, "Machen, Arthur", r"Tales of Horror|Dog and Duck|Islington|Three Impostors", r"Machen"),
    (F, "Hodgson, William Hope", r"Carnacki The Ghost Finder", r"Hodgson"),
    (F, "Blackwood, Algernon", r"Kit-Bag", r"Blackwood"),
    (F, "Merritt, Abraham", r"Collected Short Stories|Last Poet|When Old Gods Wake|White Road|Face In The Abyss", r"Merritt"),
    (S, "Weinbaum, Stanley G.", r"Collected Short Fiction|Black Flame|New Adam|Dark Other|Red Peri|Planet of Doubt|Flight on Titan|Graph|Smothered Seas|Martian Odyssey|Valley of Dreams|Worlds of If|Ideal|Point of View|Pygmalion", r"Weinbaum"),
    (S, "Kline, Otis Adelbert", r"Vision of Venus|Spawn of the Comet|Malignant Entity|Metal Monster|Revenge of the Robot|Swordsman of Mars|Planet of Peril|Maza of the Moon|Stranger from Smallness|Thing That Walked", r"Kline"),
    (S, "Zagat, Arthur Leo", r"Lost in Time|No Escape from Destiny|Cavern of the Shining Pool|Death-Cloud|Great Dome of Mercury|Green Ray|Land Where Time Stood Still|Revolt of the Machines|Song of the Cakes|Two Moons|Venus Mines|When the Sleepers Woke|Drink We Deep", r"Zagat"),
    (S, "Bryusov, Valeri", r"Republic", r"Bryusov"),
    (S, "Capek, Karel", r"Newts", r"Capek"),
]


DROP = r"Russia in the Shadows|Swampers|Hibiscus|Fugitive Anne|Jan of the Jungle|Wet Magic|Magic World|Dragon Tamers|Australian Tales|Holy Terror|First Men in the Moon"


def pga_url(u):
    m = re.search(r"(ebooks\d+/\d{7})", u)
    return ("https://gutenberg.net.au/" + m.group(1)) if m else None


def main():
    idx = uspg.load("raw/pgus/pg_catalog.csv")
    rows, seen = [], set()

    def add(shelf, author, title, url):
        base = pga_url(url)
        if re.search(DROP, title):
            return
        if not base or base in seen:
            return
        seen.add(base)
        num = uspg.lookup(idx, author, title) or ""
        rows.append((shelf, author, title, base, num))

    for line in open("pga_sf.tsv"):
        author, dates, title, url = line.rstrip("\n").split("\t")
        if author not in AUTH:
            continue
        if author in KEEP and not re.search(KEEP[author], title):
            continue
        if author == "Lovecraft, Howard Phillips" and "Horror in Literature" in title:
            continue
        shelf = AUTH[author]
        for (a, pat), s in TITLE_SHELF.items():
            if a == author and re.search(pat, title):
                shelf = s
        add(shelf, author, title, url)

    for line in open("pgau_all.tsv", encoding="utf-8", errors="replace"):
        f = line.rstrip("\n").split("\t")
        if len(f) < 4:
            continue
        pid, author, title, urls = f
        whole = author + " " + title
        for shelf, canon, tpat, apat in INDEX_EXTRA:
            if re.search(apat, whole) and re.search(tpat, title or author):
                url = urls.split()[0] if urls else f"/ebooks{pid[:2]}/{pid}1h.html"
                add(shelf, canon, title or author, url)

    with open("pga_pick.tsv", "w") as out:
        for r in rows:
            out.write("\t".join(r) + "\n")
    print(len(rows), "picked;", sum(1 for r in rows if r[4] and int(r[4]) <= 70173), "already in our US PG dump")


if __name__ == "__main__":
    main()
