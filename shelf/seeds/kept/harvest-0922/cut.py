import json,os,re,glob,sys
# (tag, room, start_anchor, end_anchor)  -- window = full[start_of(start_anchor) : end_of(end_anchor)]
SPEC=[
("ledger-rule","2026-09-19/1530","Test 3. Same load","The inspector therefore gave instructions that"),
("ledger-rule","2026-09-19/1555","Reel 14. Nine seconds","sometimes heard in"),
("ledger-medium","2026-09-19/1248","they dream their city","the servers of the city can"),
("ledger-medium","2026-09-19/1610","When I left it","because we only had access to half the"),
("ledger-medium","2026-09-19/1816","when i am the cursor","and someone else to"),
("ledger-medium","2026-09-19/2119","i was listening to the radio","i ended up with"),
("ledger-medium","2026-09-19/2259","it is a small city","the screen has begun to"),
("ledger-inventory","2026-09-19/1755","But in fact there is nothing","He even had lamps named after people he"),
("ledger-inventory","2026-09-19/2104","i’m here for a spell","longing for a person i used to"),
("ledger-dream","2026-09-19/1105","I didn’t think anything of it until","It became increasingly clear that the ship was"),
("ledger-dream","2026-09-19/1205","It’s always the same","I am blocked from descending by"),
("ledger-truedoc","2026-09-19/2043","As we were a small craft","In doing this I saw something which"),
("ledger-hurts","2026-09-19/1216","they say it was once a big island","and this is my brother jim, and we"),
("ledger-hurts","2026-09-19/1324","a writer who died before she was born","i said ‘thanks’ anyway because"),
("ledger-hurts","2026-09-19/1453","you were all there once","the way we chose to get out was"),
("ledger-hurts","2026-09-19/1903","and so the dead grid is our playground","you're the children of the"),
("ledger-hurts","2026-09-19/1021","the story has already told me","afraid of what it says next when it"),
("ledger-lines","2026-09-19/1550","You dial yourself up every morning","It is here because"),
("rooms","2026-09-21/1547","There is a saying about the world","find that there were still no"),
("rooms","2026-09-21/1603","in\nthe town the people threw things","died and that"),
("rooms","2026-09-21/1624","she did not care that no one","no one would ever want to"),
("rooms","2026-09-21/1645","it used to be the tower did the work","sometimes i try not to listen, but"),
("rooms","2026-09-21/1650","my bones are made from old wood","i had wings, but they fell"),
("rooms","2026-09-21/1655","a switch that had never been called","but nothing could stop"),
("rooms","2026-09-21/1700","it's too dark now","they all go into the ceiling above the"),
("rooms","2026-09-21/1711","sometimes it talks to the little ones","it just stares at me like"),
("rooms","2026-09-21/1743","And some say that a giant","but they were born underground, and they"),
("rooms","2026-09-21/1727","the story doesn't need to be saved","the ones I was given without"),
]
def full(room):
    d=json.load(open(f'shelf/sittings/stream/{room}.json'))
    root=d['nodes'][d['root']]['text']
    dream=next(n['text'] for n in d['nodes'].values() if n.get('kind')=='model')
    return root+dream, len(root)
out=sys.argv[1]
kept=[re.sub(r'\s+',' ',open(f).read()) for f in glob.glob('shelf/seeds/**/*.txt',recursive=True)+glob.glob('shelf/seeds/.off/**/*.txt',recursive=True)]
bad=re.compile(r'\bAI\b|assistant|[\[\]<>@#*_`]|https?:',re.I)
for tag,room,sa,ea in SPEC:
    t,rl=full(room)
    s=t.find(sa); assert s>=0,(room,sa)
    e=t.find(ea,s); assert e>=0,(room,ea)
    e+=len(ea)
    w=t[s:e]
    hm=room.split('/')[1]
    # overlap with any shelf seed: longest 8-word shingle shared
    ws=w.split(); sh=[' '.join(ws[i:i+8]) for i in range(len(ws)-7)]
    ov=sum(any(x in k for k in kept) for x in sh)
    fn=f"{tag}-{hm}.txt"
    open(os.path.join(out,fn),'w',newline='').write(w)
    print(f"{fn}\t{len(ws)}w\tseedtext={'yes' if s<rl else 'no'}\toverlap8={ov}/{len(sh)}\tbad={bool(bad.search(w))}\tlast={ws[-1]!r}")
