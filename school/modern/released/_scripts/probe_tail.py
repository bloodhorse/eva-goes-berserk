import sys, os
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "watts.py")).read().rsplit("main()", 1)[0]
g = {"__file__": os.path.abspath(__file__)}
exec(src, g)
raw = "/Users/bekh/tower/forge/eva-goes-berserk/school/modern/released/watts/raw/"
for pdf, slug, title, year in g["STORIES"][:-1]:
    ps = g["clean_story"](open(raw + pdf, "rb").read(), slug).strip().split("\n\n")
    print("##", slug, len(ps), "|", ps[0][:50])
    for p in ps[-int(sys.argv[1]):]:
        print("   ", p[:int(sys.argv[2])])
