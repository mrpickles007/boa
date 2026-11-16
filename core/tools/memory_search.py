#!/usr/bin/env python3
"""Memory search: find memory blocks (`@@@memory-<N> … @endmemory`, see memory_lint.py) — current ones by default.

Usage:  python3 -I .boa/tools/memory_search.py [filters] [--all] [--brief] [--limit N] [path...]
        python3 -I .boa/tools/memory_search.py --query "free text" [filters] [--all] [--brief] [--limit N] [path...]
        python3 -I .boa/tools/memory_search.py --chain memory-N [path...]
        python3 -I .boa/tools/memory_search.py --next-id [path...]
  --keyword W   the word (case-insensitive) in the block's keywords, brief or text; several: all must match
  --type T      the block's type is T (a type of .boa/memory-types.json); several: any of them
  --moment M    the types of recall moment M (memory-types.json: start, error, decision, …)
  --task T-NNN  the task id stands alone in the keywords, brief or text; several: all must match
  --since/--until DATE   the block's datetime is at or after / at or before DATE (YYYY-MM-DD = that whole UTC day,
                or YYYY-MM-DDTHH:MM:SSZ)
  --error TEXT  recall on a failure: the blocks of the `error` moment's types (gotcha, trap, lesson, edgecase, …)
                ranked by how many of the error's words (3+ letters, no common words) they share (at least two, or
                one when the error has fewer than three), best first, at most --limit (default 5)
  --query TEXT  hybrid ranked search, best first, at most --limit (default 5), after the other filters:
                (1) BM25 over the blocks (keywords, brief, text) finds the candidates sharing a word with the query
                (2+ letters, digits or marks in any script, case and Latin/Greek/Cyrillic accents folded,
                Han/kana runs also as character bigrams, no common words; BM25 is written here
                with the standard library, not taken from a package, because this fallback must work without the
                environment); (2) from each candidate, the sentences holding a query word (its brief
                when only its keywords hold one); (3) the query and those sentences are embedded with the
                environment `boa install` puts in .boa/embed/ (memory_embed.py; computed at query time, no vector
                database) and (4) each candidate's best cosine similarity, scaled to the best candidate's, is weighted
                equally with its BM25 score, scaled the same way; (5) no false zero: with fewer BM25 candidates than
                --limit, every memory left by the filters is compared by meaning (its keywords, brief and text, the
                text cut to its first sentences for the model's input window; vectors cached by content hash in
                .boa/embed/cache/memory-vectors.json — computed at write time by memory_write.py, lazily here for
                anything missing; a cache, safe to delete, never a database) and those at cosine
                0.5 or more are added after the BM25 ones, so a memory in another language with no shared word is
                still found. The query and the re-rank sentences are embedded in their own call; the missing vectors
                are filled in chunks of 256, saved after each, within 20 s: what is left is said ("N memories not yet
                compared — they will be next time") and filled by the next queries. The line before the last says how the matches were ranked and whether the fallback ran;
                when the environment is missing or fails it prints a WARNING naming the fix and gives the BM25 result
                (never fails because of it)
  --warm        cache the vector of every memory not cached yet, in chunks, no time limit (boa install runs it
                once; best effort, exit 0); --warm-ids N,M: only those memories (memory_write's detached child)
  --all         superseded blocks too (default: current ones only — no `superseded-by`)
  --chain ID    the supersession chain of a memory: its predecessors (what it superseded, recursively) and its
                successors up to the current head, oldest first, the head marked
  --next-id     the next free id (the highest of the bank and the id ledger, plus one) — informative only: ids are
                assigned by memory_write.py
  --brief       one line per match: `memory-N file:line datetime type brief`
  path          files or directories (every *.md under them); default: the project's memory bank (BOA_MEMORY_DIR)
                and the lead dir (BOA_LEAD_DIR of the main checkout, also from a worktree; drafts included)
Matches print in time order (oldest first; --error and --query: best first), each as `== memory-N <file>:<line>` and
the block. When --limit leaves ranked matches out (--error, --query), the line before the last says so: "memory-search:
<m> more ranked match(es) not shown (--limit <L>): run again with a higher --limit to see them" (never a silent cut).
Last line: "memory-search: <n> match(es) in <k> block(s)". Exit 0 with a match, 1 with none, 2 on a usage
error (also --limit below 1, a query with no searchable word, --query with --error, --chain or --next-id).
Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import itertools
import json
import math
import os
import re
import subprocess
import sys
import time
import unicodedata

sys.dont_write_bytecode = True  # importing the sibling modules must leave no __pycache__ behind (zero residue)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import boa_config  # noqa: E402  (sibling module; `python3 -I` leaves the script directory off sys.path)
import memory_lint as ml  # noqa: E402
import memory_embed  # noqa: E402
import memory_types  # noqa: E402

UTC = datetime.timezone.utc
COMMON = set("""the and for with from that this was were are has have had not but its into onto than then there
their they them you your our out off over under when what which while who will would could should about after
before does did done how why all any can may also just only very""".split())
STOP = COMMON | set("""error failed failure cannot can't could not line file""".split())   # error recall
POOL = 50           # the best BM25 candidates handed to the re-rank
WEIGHT = 0.5        # the cosine's share of the final score (BM25 has the rest)
EMBED_TIMEOUT = 60  # seconds for one embedding call (query + sentences)
K1, B = 1.5, 0.75   # BM25 (Okapi; the idf of Lucene, never negative)
GRAM_WEIGHT = 0.3   # a Han/kana bigram match counts this much of a whole-word match
SEM_MIN = 0.5       # the semantic fallback's least cosine similarity (unrelated texts score well below it)
VECTORS = "memory-vectors.json"
SUMMARY_CHARS = 500  # about the model's input window (128 tokens) for one memory's vector
FILL_CHUNK = 256    # memories per embedding call when the vector cache is filled
NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}   # no console window flashing
FILL_BUDGET = 20    # seconds a query may spend filling the vector cache (the rest waits for the next query)
JOINERS = "._-"     # inside a word only, between two word characters (T-123, a.b, snake_case)
LGC = ("LATIN", "GREEK", "CYRILLIC")   # the scripts whose combining marks are accents, folded away


def bound(value: str, end: bool) -> datetime.datetime:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        day = datetime.datetime.fromisoformat(value).replace(tzinfo=UTC)
        return day + datetime.timedelta(days=1, seconds=-1) if end else day
    when = ml.parse_datetime(value)
    if when is None:
        raise ValueError(value)
    return when


def fold(text: str) -> str:
    """Case and accents folded the same way for queries and memories: casefold and NFKD, then the combining marks
    of Latin, Greek and Cyrillic letters dropped (`R` + e-acute + `seau` = `reseau`); every other script keeps its
    marks (Indic vowel signs, Thai tone marks, the kana voicing marks: katakana `ga su` stays apart from `ka su`),
    recomposed with NFC."""
    out: list[str] = []
    accent = False
    for c in unicodedata.normalize("NFKD", text.casefold()):
        if unicodedata.category(c)[0] == "M":
            if accent:
                continue
        else:
            accent = c < "\x80" or unicodedata.name(c, "").startswith(LGC)
        out.append(c)
    return unicodedata.normalize("NFC", "".join(out))


def wordchar(c: str) -> bool:
    return unicodedata.category(c)[0] in "LNM"   # letters, digits and marks of any script


def cjk(c: str) -> bool:
    """Han, Hiragana or Katakana: scripts written without spaces between words."""
    o = ord(c)
    return 0x3040 <= o <= 0x30FF or 0x31F0 <= o <= 0x31FF or 0x3400 <= o <= 0x4DBF or 0x4E00 <= o <= 0x9FFF \
        or 0xF900 <= o <= 0xFAFF or 0x20000 <= o <= 0x3134F


def scan(text: str) -> list[str]:
    """The words (2+ characters) of a folded text: letters, digits and marks of any script, `._-` inside only."""
    out: list[str] = []
    cur: list[str] = []
    for i, c in enumerate(text + " "):
        if wordchar(c) or (c in JOINERS and cur and i + 1 < len(text) and wordchar(text[i + 1])):
            cur.append(c)
            continue
        if len(cur) >= 2:
            out.append("".join(cur))
        cur = []
    return out


ASCII_WORD = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*")   # scan() on lower-case ASCII, faster


def terms(text: str) -> tuple[list[str], list[str]]:
    """The searchable words of a text (repeats kept: term frequency) and the character bigrams of its Han/kana runs.
    A word that switches between Han/kana and other characters also yields each part (`Server` followed by a katakana
    word gives `server` and the katakana word); a Han/kana run of 2+ characters yields its bigrams (a run of four Han
    characters ABCD gives AB, BC, CD), weighed lower than whole words (GRAM_WEIGHT) so a query of its first three
    characters ABC still finds it."""
    if text.isascii():
        return [w for w in ASCII_WORD.findall(text.lower()) if len(w) >= 2 and w not in COMMON], []
    words: list[str] = []
    grams: list[str] = []
    for w in scan(fold(text)):
        words.append(w)
        if w.isascii():
            continue
        parts = ["".join(g) for _, g in itertools.groupby(w, key=cjk)]   # Han/kana runs and the rest
        if len(parts) > 1:
            words += [x.strip("._-") for x in parts if len(x.strip("._-")) >= 2]
        for x in parts:
            if cjk(x[0]) and len(x) >= 2:   # a 2-character run is its own bigram: it meets longer runs' bigrams
                grams += [x[j:j + 2] for j in range(len(x) - 1)]
    return [w for w in words if w not in COMMON], grams


def words(text: str) -> set[str]:
    main, grams = terms(text)
    return {w for w in main + grams if (len(w) >= 3 or cjk(w[0])) and w not in STOP}


def hay(b: ml.Block) -> str:
    return " ".join((b.fields.get("keywords", ""), b.fields.get("brief", ""), b.text))


def tokens(text: str) -> list[str]:
    """Every search term of a text: its words, then its Han/kana bigrams."""
    main, grams = terms(text)
    return main + grams


def bm25(docs: list[list[str]], query: set[str], lengths: list[int] | None = None) -> list[float]:
    """Okapi BM25 of each doc for the query terms; `lengths` = the doc lengths to normalise by (default: len(doc))."""
    n = len(docs)
    lengths = lengths if lengths is not None else [len(d) for d in docs]
    avg = sum(lengths) / n if n else 0.0
    df = collections.Counter(t for d in docs for t in set(d) & query)
    idf = {t: math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5)) for t in df}
    out = []
    for d, length in zip(docs, lengths):
        tf = collections.Counter(t for t in d if t in idf)
        norm = K1 * (1 - B + B * length / avg) if avg else K1
        out.append(sum(idf[t] * f * (K1 + 1) / (f + norm) for t, f in tf.items()))
    return out


def sentences(b: ml.Block) -> list[str]:
    """The block's brief and its text cut into sentences (hard-wrapped lines joined; paragraphs and list items end one)."""
    out = [" ".join(b.fields.get("brief", "").split())]
    for para in re.split(r"\n\s*\n|\n(?=\s*(?:[-*+]|\d+[.)])\s)", b.text):
        out += re.split(r"(?<=[.!?])\s+(?=[A-Z0-9`(\"'])", " ".join(para.split()))
    return [x for x in out if x]


def keyword_sentences(b: ml.Block, query: set[str]) -> list[str]:
    every = sentences(b)
    return [x for x in every if query & set(tokens(x))] or every[:1] or [b.fields.get("keywords", "")]


def embedder(main: str) -> tuple[list[str] | None, str]:
    """The command embedding texts, or None and the WARNING naming the fix; the second item is the model's identity
    (name@revision: what the vector cache is keyed on) when the command is there."""
    env = memory_embed.paths(main)
    try:
        with open(env["stamp"], encoding="utf-8") as fh:
            model = json.load(fh)["model"]
        name, revision = model["name"], str(model.get("revision", ""))
    except (OSError, ValueError, KeyError, TypeError):
        name = revision = None
    if not isinstance(name, str) or not name or not os.path.isfile(env["python"]):
        return None, f"the memory search environment is missing ({env['dir']}): re-run `boa install`"
    here = os.path.dirname(os.path.abspath(__file__))
    return [env["python"], "-I", os.path.join(here, "memory_embed.py"), "embed", name, env["model"]], \
        f"{name}@{revision}"


def embed(cmd: list[str], texts: list[str], timeout: float = EMBED_TIMEOUT) -> list[list[float]]:
    """One vector per text through the environment's command; ValueError (the reason) on any failure."""
    try:
        r = subprocess.run(cmd, input=json.dumps(texts), capture_output=True, text=True, encoding="utf-8",
                           timeout=timeout, **NO_WINDOW)
    except subprocess.TimeoutExpired:
        raise ValueError(f"the embedding call timed out after {timeout:.0f}s") from None
    except OSError as exc:
        raise ValueError(f"the embedding call did not start: {exc}") from None
    if r.returncode != 0:
        last = ([x for x in r.stderr.splitlines() if x.strip()] or ["no message"])[-1].strip()
        last = last if len(last) <= 200 else last[:200] + " [cut at 200 characters: the embedder's own stderr]"
        raise ValueError(f"the embedding call failed (exit {r.returncode}): {last}")
    try:
        vecs = json.loads(r.stdout)
    except ValueError:
        raise ValueError("the embedding call printed no JSON") from None
    if not isinstance(vecs, list) or len(vecs) != len(texts):
        raise ValueError(f"the embedding call returned {len(vecs) if isinstance(vecs, list) else 'no'} vector(s) "
                         f"for {len(texts)} text(s)")
    dim = len(vecs[0]) if vecs and isinstance(vecs[0], list) else 0
    for v in vecs:
        if not isinstance(v, list) or len(v) != dim or not dim or not all(
                isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in v):
            raise ValueError("the embedding call returned a malformed vector (not finite numbers of one length)")
    return vecs


def cosine(a: list[float], b: list[float]) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def summary(b: ml.Block) -> str:
    """What the semantic fallback embeds for a memory: the fields BM25 indexes — keywords, brief and text — with the
    text cut to its first sentences when the whole would pass the model's input window (SUMMARY_CHARS). Its hash
    keys the cached vector: a change to any of the three re-embeds the memory."""
    head = " ".join(x for x in (b.fields.get("keywords", ""), " ".join(b.fields.get("brief", "").split())) if x)
    text = " ".join(b.text.split())
    if len(head) + 1 + len(text) > SUMMARY_CHARS:
        kept: list[str] = []
        for x in sentences(b)[1:]:
            if kept and len(head) + 1 + len(" ".join(kept + [x])) > SUMMARY_CHARS:
                break
            kept.append(x)
        text = " ".join(kept)
    return " ".join(x for x in (head, text) if x)


class VectorCache:
    """Each memory's summary vector by content hash, in .boa/embed/cache/memory-vectors.json of the main checkout: a
    cache (filled lazily for new or changed memories; a missing or unreadable file, or one of another model identity
    — name@revision — is simply rebuilt), never a database. save() merges: it re-reads the file, adds its own new
    entries, drops only the stale keys it saw at its own read (an entry another process added meanwhile stays), then
    replaces the file atomically; a write that fails is skipped."""

    def __init__(self, main: str, model: str):
        self.path = os.path.join(memory_embed.paths(main)["dir"], "cache", VECTORS)
        self.model = model
        self.vectors = self.read()
        self.seen = set(self.vectors)   # the keys of this read: the only ones a prune may drop
        self.added: dict[str, list[float]] = {}

    def read(self) -> dict[str, list[float]]:
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return {}
        if not (isinstance(data, dict) and data.get("model") == self.model and isinstance(data.get("vectors"), dict)):
            return {}
        return {k: v for k, v in data["vectors"].items() if isinstance(v, list) and v and all(
            isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in v)}

    @staticmethod
    def key(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def add(self, pairs) -> None:
        for k, v in pairs:
            self.vectors[k] = self.added[k] = v

    def save(self, keep: set[str] | None = None) -> None:
        # best effort: two processes saving at once may lose an entry; a lost entry is simply recomputed later
        if not os.path.isdir(os.path.dirname(os.path.dirname(self.path))):
            return   # the environment is gone (uninstalled meanwhile): leave nothing behind
        merged = {**self.read(), **self.added}
        if keep is not None:
            for k in self.seen - keep:
                merged.pop(k, None)
        tmp = f"{self.path}.{os.getpid()}.tmp"
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"model": self.model, "vectors": merged}, fh)
            os.replace(tmp, self.path)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        self.vectors = {**merged, **self.vectors}


def memories(n: int) -> str:
    return f"{n} memory" if n == 1 else f"{n} memories"


def test_number(name: str, default: int) -> int:
    """A positive whole number from a test-only variable (memory_lint.test_env), else the default."""
    value = ml.test_env(name)
    return int(value) if value and value.isdigit() and int(value) > 0 else default


def fill(cmd: list[str], cache: VectorCache, texts: dict[str, str], budget: float | None) -> tuple[int, str]:
    """Embed the uncached `texts` (key -> summary) in chunks of FILL_CHUNK, saving after each one, until done or the
    time `budget` (seconds; None = no limit) is spent: (how many are still missing, the reason it stopped or '')."""
    chunk = test_number("BOA_MEMORY_FILL_CHUNK", FILL_CHUNK)
    todo = list(texts.items())
    start = time.monotonic()
    first = True
    while todo:
        left = None if budget is None else budget - (time.monotonic() - start)
        if not first and left is not None and left <= 1:
            return len(todo), ""
        part, todo = todo[:chunk], todo[chunk:]
        # the first chunk always gets the full timeout: a slow machine still makes progress at every query
        timeout = EMBED_TIMEOUT if first or left is None else min(EMBED_TIMEOUT, left)
        first = False
        try:
            vecs = embed(cmd, [t for _, t in part], timeout)
        except ValueError as exc:
            return len(part) + len(todo), str(exc)
        cache.add(zip((k for k, _ in part), vecs))
        cache.save()
    return 0, ""


def warm(main: str, blocks: list[ml.Block], budget: float | None) -> str:
    """Cache the vectors of `blocks` not cached yet (memory_write's detached child: the memories it wrote; boa
    install: the whole bank, no budget). Returns one line saying what happened. Never raises."""
    try:
        cmd, model = embedder(main)
        if cmd is None:
            return f"memory search vectors not computed (the search computes them later): {model}"
        cache = VectorCache(main, model)
        texts = {}
        for b in blocks:
            k = cache.key(summary(b))
            if k not in cache.vectors:
                texts[k] = summary(b)
        missing, why = fill(cmd, cache, texts, budget)
        return f"memory search vectors: {len(texts) - missing} computed, {missing} still missing" + \
            (f" ({why})" if why else "")
    except Exception as exc:  # noqa: BLE001  (best effort: a write or an install never fails because of it)
        return f"memory search vectors not computed (the search computes them later): {exc}"


def rank(blocks: list[ml.Block], query: str, main: str, limit: int,
         every: list[ml.Block] | None = None) -> tuple[list[ml.Block], str]:
    """--query: EVERY match ranked best first, uncut (the re-rank takes the best POOL BM25 candidates, the rest follow
    in BM25 order; the fallback adds every memory found by meaning; main() shows --limit of them and says how many
    more), and the line saying how (module docstring, --query). `every` = all the
    loaded blocks, given when the default paths were searched: the vector cache then drops the entries of memories
    that no longer exist."""
    qmain, qgrams = terms(query)
    q = set(qmain) | set(qgrams)
    docs = [terms(hay(b)) for b in blocks]
    lengths = [len(d[0]) for d in docs]   # whole words only: bigrams do not lengthen a memory
    scores = [w + GRAM_WEIGHT * g for w, g in zip(bm25([d[0] for d in docs], set(qmain), lengths),
                                                  bm25([d[1] for d in docs], set(qgrams), lengths))]
    newest = datetime.datetime.min.replace(tzinfo=UTC)
    every_cand = sorted(((s, b) for s, b in zip(scores, blocks) if s > 0),
                        key=lambda x: (-x[0], -(x[1].when() or newest).timestamp()))
    cands = every_cand[:POOL]                       # re-ranked by meaning
    beyond = [b for _, b in every_cand[POOL:]]      # kept after them in BM25 order: never a silent cut
    cmd, model = embedder(main)
    if cmd is None:
        if not cands:
            return [], f"memory-search: WARNING no re-rank and no search by meaning: {model}"
        return [b for _, b in every_cand], f"memory-search: WARNING ranked by BM25 only: {model}"
    # the query and the re-rank sentences in their own call: the re-rank never waits on the cache fill
    groups = [keyword_sentences(b, q) for _, b in cands]
    try:
        vecs = embed(cmd, [query] + [x for g in groups for x in g])
    except ValueError as exc:
        why = f"{exc}; re-run `boa install`"
        if not cands:
            return [], f"memory-search: WARNING no re-rank and no search by meaning: {why}"
        return [b for _, b in every_cand], f"memory-search: WARNING ranked by BM25 only: {why}"
    qv, at = vecs[0], 1
    ranked: list[ml.Block] = []
    if cands:
        rel = []
        for g in groups:
            rel.append(max(0.0, max(cosine(qv, v) for v in vecs[at:at + len(g)])))
            at += len(g)
        top_b, top_c = cands[0][0], max(rel)
        final = [(WEIGHT * (c / top_c if top_c else 0.0) + (1 - WEIGHT) * s / top_b, s, b)
                 for c, (s, b) in zip(rel, cands)]
        final.sort(key=lambda x: (-x[0], -x[1], -(x[2].when() or newest).timestamp()))
        ranked = [b for _, _, b in final] + beyond
    how = "memory-search: ranked by BM25 + sentence re-rank (embedding cosine)" if cands else \
        "memory-search: no BM25 candidate"
    if len(every_cand) >= limit:
        return ranked, how
    # no false zero: every memory left by the filters, by meaning, from the cache (filled now within a time budget)
    cache = VectorCache(main, model)
    keys = {id(b): cache.key(summary(b)) for b in blocks}
    texts = {keys[id(b)]: summary(b) for b in blocks if keys[id(b)] not in cache.vectors}
    missing, why = fill(cmd, cache, texts, test_number("BOA_MEMORY_FILL_BUDGET", FILL_BUDGET))
    if every is not None:
        keep = {cache.key(summary(b)) for b in every}
        if cache.seen - keep:
            cache.save(keep)
    seen = {id(b) for b in ranked}
    near = sorted(((cosine(qv, cache.vectors[keys[id(b)]]), b) for b in blocks
                   if id(b) not in seen and len(cache.vectors.get(keys[id(b)], ())) == len(qv)),
                  key=lambda x: (-x[0], -(x[1].when() or newest).timestamp()))
    extra = [b for c, b in near if c >= SEM_MIN]   # every one found: main() shows --limit and says how many more
    later = f"; {memories(missing)} not yet compared — they will be next time" + (f" ({why})" if why else "") \
        if missing else ""
    return ranked + extra, (f"{how}; semantic fallback (fewer BM25 candidates than --limit {limit}): every memory "
                            f"compared by meaning, {len(extra)} more found ({memories(len(texts) - missing)} "
                            f"embedded, the rest from the cache){later}")


def load_blocks(paths: list[str], names: list[str]) -> list[ml.Block]:
    blocks: list[ml.Block] = []
    for f in ml.files_of(paths):
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        blocks += [b for b in ml.parse_blocks(f, text, names)[0] if b.id is not None]
        blocks += [b for b in ml.parse_blocks(f, text, names, drafts=True)[0] if b.id is None]
    return blocks


def recall_error(blocks: list[ml.Block], types: memory_types.Types, text: str, limit: int) -> list[tuple[int, ml.Block]]:
    want = words(text)
    need = 2 if len(want) >= 3 else 1
    allowed = set(types.moment_types("error"))
    scored = []
    for b in blocks:
        if b.fields.get("type") not in allowed or not b.current:
            continue
        score = len(want & words(hay(b)))
        if score >= need:
            scored.append((score, b))
    scored.sort(key=lambda x: (-x[0], -(x[1].id or 0)))
    return scored[:limit]


def show(b: ml.Block, brief: bool) -> str:
    if brief:
        return f"{b.mid} {b.path}:{b.line} {b.fields.get('datetime', '?')} {b.fields.get('type', '?')} {b.fields.get('brief', '')}"
    return f"== {b.mid} {b.path}:{b.line}\n{b.header}\n{b.text}\n{ml.END}"


def main(argv: list[str]) -> int:
    import boa_tool
    boa_tool.on_term_exit()   # a stop mid-search still ends the embedder child and runs the finally blocks
    try:
        cfg = boa_config.load()
    except (boa_config.ConfigError, OSError, UnicodeDecodeError) as exc:   # one line naming the bad line, no traceback
        print(f"memory-search: config: {exc}", file=sys.stderr)
        return 2
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for k in ("--keyword", "--type", "--task", "--moment"):
        ap.add_argument(k, action="append", default=[])
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--error")
    ap.add_argument("--query")
    ap.add_argument("--warm", action="store_true")
    ap.add_argument("--warm-ids")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--chain")
    ap.add_argument("--next-id", action="store_true")
    ap.add_argument("--brief", action="store_true")
    ap.add_argument("paths", nargs="*")
    a = ap.parse_args(argv)
    if a.limit < 1:
        print("memory-search: --limit must be 1 or more", file=sys.stderr)
        return 2
    if a.query is not None and (a.error is not None or a.chain or a.next_id):
        print("memory-search: --query does not combine with --error, --chain or --next-id", file=sys.stderr)
        return 2
    if a.query is not None and not tokens(a.query):
        print(f"memory-search: the query {a.query!r} has no searchable word (2+ letters, not a common word)",
              file=sys.stderr)
        return 2
    try:
        types = memory_types.load()
    except memory_types.TypesError as exc:
        print(f"memory-search: {exc}", file=sys.stderr)
        return 2
    bad = [t for t in a.type if t not in types.names] + [t for t in a.task if not ml.TASK.fullmatch(t)] \
        + [m for m in a.moment if m not in types.moments]
    if bad:
        print(f"memory-search: unknown type, recall moment or task id: {', '.join(bad)} (types: {', '.join(types.names)}; "
              f"moments: {', '.join(types.moments)}; task ids: T-NNN)", file=sys.stderr)
        return 2
    try:
        since = bound(a.since, False) if a.since else None
        until = bound(a.until, True) if a.until else None
    except ValueError as exc:
        print(f"memory-search: not a date: {exc}", file=sys.stderr)
        return 2
    mdir = ml.memory_dir()
    try:
        main_dir = boa_config.main_of(ml.ROOT)
        lead = os.path.join(main_dir, cfg["BOA_LEAD_DIR"])   # the main checkout's, also from a worktree
    except boa_config.ConfigError as exc:
        print(f"memory-search: {exc}", file=sys.stderr)
        return 2
    default = [p for p in (mdir, lead) if os.path.exists(p)]
    paths = a.paths or default
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        print(f"memory-search: not found: {', '.join(missing)}", file=sys.stderr)
        return 2
    blocks = load_blocks(paths, types.names)
    by_id = {b.id: b for b in blocks if b.id}
    if a.warm or a.warm_ids:
        ids = {int(x) for x in re.findall(r"\d+", a.warm_ids or "")}
        print(f"memory-search: {warm(main_dir, [b for b in blocks if a.warm or b.id in ids], None)}")
        return 0

    if a.next_id:
        entries, _ = ml.read_ledger(os.path.join(mdir, ml.LEDGER))
        print(f"memory-{max([0] + list(by_id) + list(entries)) + 1}")
        return 0
    if a.chain:
        m = ml.MID.fullmatch(a.chain)
        if not m or int(m.group(1)) not in by_id:
            print(f"memory-search: no memory {a.chain}", file=sys.stderr)
            return 2 if not m else 1
        start = by_id[int(m.group(1))]
        chain: dict[int, ml.Block] = {}
        todo = [start.id]
        while todo:  # predecessors, recursively (a merge has several)
            i = todo.pop()
            if i in chain or i not in by_id:
                continue
            chain[i] = by_id[i]
            todo += ml.sup(by_id[i])
        cur, seen = start, {start.id}
        while not cur.current:  # successors up to the head
            s = ml.succ_of(cur)
            if s is None or s not in by_id or s in seen:
                print(f"memory-search: the chain breaks after {cur.mid} (run memory_lint.py)", file=sys.stderr)
                return 1
            seen.add(s)
            cur = by_id[s]
            chain[cur.id] = cur
        for i in sorted(chain):
            b = chain[i]
            mark = "  <- current head" if b.current else f"  (superseded by {b.fields['superseded-by']})"
            print(show(b, True) + mark)
        print(f"memory-search: chain of {memories(len(chain))}, current head memory-{cur.id}")
        return 0

    if a.error is not None:
        hits = [b for _, b in recall_error(blocks, types, a.error, max(len(blocks), 1))]
    else:
        allowed = set(a.type) | {t for m in a.moment for t in types.moment_types(m)}
        hits = []
        for b in blocks:
            h = hay(b)
            when = b.when()
            if not a.all and not b.current:
                continue
            if allowed and b.fields.get("type") not in allowed:
                continue
            if any(k.lower() not in h.lower() for k in a.keyword):
                continue
            if any(not re.search(r"(?<![A-Za-z0-9-])" + re.escape(t) + r"(?![0-9A-Za-z])", h) for t in a.task):
                continue
            if (since or until) and (when is None or (since and when < since) or (until and when > until)):
                continue
            hits.append(b)
        far = datetime.datetime.max.replace(tzinfo=UTC)
        hits.sort(key=lambda b: (b.when() or far, b.path, b.line))
    how = ""
    more = 0
    if a.query is not None:
        hits, how = rank(hits, a.query, main_dir, a.limit, blocks if not a.paths else None)
        if how.startswith("memory-search: WARNING"):
            print(how, file=sys.stderr)
    if a.query is not None or a.error is not None:
        hits, more = hits[:a.limit], max(0, len(hits) - a.limit)
    for b in hits:
        print(show(b, a.brief))
    if how:
        print(how)
    if more:   # never a silent cut: say how many ranked matches the limit left out and how to see them
        print(f"memory-search: {more} more ranked match(es) not shown (--limit {a.limit}): run again with a higher "
              "--limit to see them")
    print(f"memory-search: {len(hits)} match(es) in {len(blocks)} block(s)")
    return 0 if hits else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
