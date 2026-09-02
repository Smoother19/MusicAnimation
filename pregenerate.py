import sys
import time
from pathlib import Path

import corpus
import presets


def generate(filename, force=False):
    from transcription import analyze

    name = presets.stem(filename)
    meta = presets.describe(filename)
    if meta and meta["complete"] and not force:
        print(f"{name:16s} deja present ({meta['notes']} notes, "
              f"genere le {meta['generated'][:10]}) -- --force pour le refaire")
        return meta

    source = presets.SOUNDS / Path(filename).name
    if not source.exists():
        print(f"{name:16s} INTROUVABLE : {source}")
        return None

    print(f"{name:16s} transcription...", end=" ", flush=True)
    started = time.perf_counter()
    notes = analyze(str(source))
    elapsed = time.perf_counter() - started

    meta = presets.save(filename, notes, seconds=elapsed)
    print(f"{meta['notes']} notes en {elapsed:.0f} s  "
          + ", ".join(f"{k} {v}" for k, v in meta["by_instrument"].items()))
    return meta


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}

    if "--list" in flags:
        for name, data in presets.status():
            print(f"{name:16s} {data['notes']:5d} notes  "
                  f"{data['generated'][:16].replace('T', ' ')}")
        sys.exit()

    if args:
        targets = args
    elif "--all" in flags:
        targets = [Path(corpus.get(n)["mix"]).name for n in corpus.available()]
    else:
        targets = [Path(corpus.get(n)["mix"]).name for n in corpus.DEMO]

    print(f"a generer : {', '.join(targets)}\n")
    for filename in targets:
        generate(filename, force="--force" in flags)
    print(f"\npresets dans {presets.PRESETS.resolve()}")
