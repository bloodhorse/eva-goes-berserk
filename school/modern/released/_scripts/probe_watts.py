import sys, os, gzip
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "watts.py")).read().rsplit("main()", 1)[0]
g = {"__file__": os.path.abspath(__file__)}
exec(src, g)
raw = "/Users/bekh/tower/forge/eva-goes-berserk/school/modern/released/watts/raw/"
for pdf, slug, title, year in g["STORIES"]:
    ps = g["pdf_paras"](open(raw + pdf, "rb").read())
    print("##", slug, len(ps))
    for i, p in enumerate(ps[:int(sys.argv[1])]):
        print(" ", i, p[:int(sys.argv[2])])
