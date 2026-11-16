"""Generate Turkish pronunciation mp3s for every word in frontend/index.html.

Usage:  pip install edge-tts && python tools/make_audio.py
Writes frontend/audio/<n>.mp3 and frontend/audio/index.json ({word: file}).
Already generated words are skipped, so rerun after adding words.
"""
import asyncio
import json
import re
from pathlib import Path

import edge_tts

VOICE = "tr-TR-EmelNeural"
RATE = "-10%"
ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "frontend" / "index.html"
OUT = ROOT / "frontend" / "audio"


def words() -> list[str]:
    src = HTML.read_text(encoding="utf-8")
    block = re.search(r"var RAW = \[(.*?)\];", src, re.S).group(1)
    return list(dict.fromkeys(m.split("|")[0] for m in re.findall(r"'([^']*)'", block)))


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    idx_path = OUT / "index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
    todo = [w for w in words() if w not in index or not (OUT / index[w]).exists()]
    n = max([int(Path(f).stem) for f in index.values()] + [0])
    sem = asyncio.Semaphore(6)

    async def one(word: str, name: str) -> None:
        async with sem:
            for attempt in range(3):
                try:
                    await edge_tts.Communicate(word, VOICE, rate=RATE).save(str(OUT / name))
                    index[word] = name
                    return
                except Exception as e:  # network hiccups
                    if attempt == 2:
                        print("FAILED", word, e)
                    await asyncio.sleep(1 + attempt)

    jobs = []
    for w in todo:
        n += 1
        jobs.append(one(w, f"{n}.mp3"))
    await asyncio.gather(*jobs)
    idx_path.write_text(json.dumps(index, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(f"{len(todo)} generated, {len(index)} total")


if __name__ == "__main__":
    asyncio.run(main())
