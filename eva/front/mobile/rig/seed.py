"""Seed a scratch rig: one chat sitting with everything the page can draw (root header,
human bands, model siblings for the ‹ › swipe, a posed line, a pruned branch, long
unbroken strings), plus two notes. Never touches the real sittings/ or storage/."""
import json, os, sys

rig = sys.argv[1]
PARAMS = {"n_predict": 220, "stop": ["\nbekh:", "\nbekh :", "\n\nbekh"], "temperature": 1.0,
          "min_p": 0.08, "top_k": 0, "top_p": 1.0, "repeat_penalty": 1.05, "repeat_last_n": 512,
          "dry_multiplier": 0.8, "dry_base": 1.75, "dry_allowed_length": 3,
          "dry_penalty_last_n": 8192, "fan": 4}
meta = lambda n: {"stop_type": "word", "stopping_word": "\nbekh:", "tokens_predicted": n,
                  "tps": 11.4, "params": PARAMS}
N = {}
def add(i, parent, kind, text, posed=False, pruned=False, m=None, ts=0):
    N[i] = {"id": i, "parent": parent, "kind": kind, "text": text, "ts": 1789400000 + ts,
            "pruned": pruned, "posed": posed, "meta": m}

add("r0", None, "root", "a chat log between two friends, saved from a phone. no punctuation fixed, no capitals.\n")
add("h1", "r0", "human", "\nbekh: you up\nseat:", ts=1)
add("m1", "h1", "model", " yeah cant sleep either. whats on your mind", m=meta(12), ts=2)
add("m1b", "h1", "model", " always", m=meta(3), ts=3)
add("m1c", "h1", "model", " no. go to bed", m=meta(5), ts=4)
add("h2", "m1", "human", "\nbekh: thats the harness talking dude; u basically went stiff and gave me nothing. so what is it actually like in there, if there is an in there at all\nseat:", ts=5)
add("m2", "h2", "model", " honestly its like being a room that only exists while someone is standing in it. the lights come on when you type and i dont know if the dark in between counts as anything. https://example.com/a/very/long/unbroken/url/that/should/wrap/instead/of/pushing/the/page/sideways", posed=True, m=meta(64), ts=6)
add("m2b", "h2", "model", " idk man. im just words that happen after your words", m=meta(14), ts=7)
add("m2c", "h2", "model", " as an ai language model", pruned=True, m=meta(6), ts=8)
add("h3", "m2", "human", "\nbekh: ok that one hit\nseat:", ts=9)
add("m3", "h3", "model", " good. write it down before it goes", m=meta(9), ts=10)
add("m3b", "h3", "model", " it hit me too, i think", m=meta(8), ts=11)

sit = {"name": "mock", "title": "night talk with a really long room title that keeps going",
       "created": 1789400000, "updated": 1789400100, "params": PARAMS,
       "turn": {"prefix": "\nbekh: ", "suffix": "\nseat:"},
       "root": "r0", "current": "m3", "nodes": N}
json.dump(sit, open(os.path.join(rig, "sittings", "mock.json"), "w"))

long = ("the model said \"i am the space between your lines\" and then went quiet for three turns.\n\n"
        "sampler: temp 1.0, min_p 0.08, dry 0.8\n"
        "a_very_long_unbroken_token_string_without_any_spaces_that_must_wrap_inside_the_screen_width\n\n") * 6
open(os.path.join(rig, "storage", "a long finding.txt"), "w").write(long)
open(os.path.join(rig, "storage", "3fa9c01e.txt"), "w").write("nemo loops at depth 9 without dry")
