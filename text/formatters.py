import json
import os.path
import re

from talon import resource
import talon.clip as clip
from talon.voice import Context, Word, press

from ..utils import parse_word, surround, vocab, parse_words, insert

jargon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jargon.json")
jargon_substitutions = {}
with resource.open(jargon_path) as fh:
    jargon_substitutions.update(json.load(fh))

ACRONYM = (True, lambda i, word, _: word[0:1].upper())
FIRST_THREE = (True, lambda i, word, _: word[0:3] if i == 0 else "")
FIRST_FOUR = (True, lambda i, word, _: word[0:4] if i == 0 else "")
DUNDER = (
    True,
    lambda i, word, last: ("__%s" % word if i == 0 else word) + ("__" if last else ""),
)
CAMELCASE = (True, lambda i, word, _: word if i == 0 else word.capitalize())
SLASH_SEPARATED = (True, lambda i, word, _: word if i == 0 else "/" + word)
DOT_SEPARATED = (True, lambda i, word, _: word if i == 0 else "." + word)
GOLANG_PRIVATE = (
    True,
    lambda i, word, _: word.lower()
    if i == 0
    else word
    if word.upper() == word
    else word.capitalize(),
)
GOLANG_PUBLIC = (
    True,
    lambda i, word, _: word if word.upper() == word else word.capitalize(),
)
DOT_STUB = (True, lambda i, word, _: "." + word.lower() if i == 0 else word)
NO_SPACES = (True, lambda i, word, _: word)
DASH_SEPARATED = (True, lambda i, word, _: word if i == 0 else "-" + word)
DOWNSCORE_SEPARATED = (True, lambda i, word, _: word if i == 0 else "_" + word)
LOWSMASH = (True, lambda i, word, _: word.lower())
SENTENCE = (False, lambda i, word, _: word.capitalize() if i == 0 else word)

formatters = {
    # Smashed
    "acronym": ACRONYM,
    "tree": FIRST_THREE,
    "quad": FIRST_FOUR,
    "dunder": DUNDER,
    "camel": GOLANG_PRIVATE,
    "slashed": SLASH_SEPARATED,
    # Golang private/public conventions prefer SendHTML to SendHtml sendHtml
    # TODO: Consider making these the "camel" impl, pep8 prefers it as well.
    # "private": GOLANG_PRIVATE,
    "upper": GOLANG_PUBLIC,
    # Call method: for driving jetbrains style fuzzy Complete -> .fuzCom
    # "cell": DOT_STUB,
    "snake": DOWNSCORE_SEPARATED,
    "smash": NO_SPACES,
    "spine": DASH_SEPARATED,
    # Spaced
    "sentence": SENTENCE,
    "jargon": (False, lambda i, word, _: jargon_substitutions.get(word.lower(), word)),
    "title": (False, lambda i, word, _: word.capitalize()),
    "allcaps": (False, lambda i, word, _: word.upper()),
    "lowcaps": (False, lambda i, word, _: word.lower()),
    "phrase": (False, lambda i, word, _: word),
    "bold": (False, surround('*')),
    "quoted": (False, surround('"')),
    "ticked": (False, surround("'")),
    "glitched": (False, surround("`")),
    "padded": (False, surround(" ")),
}


def normalize(identifier):
    # https://stackoverflow.com/questions/29916065/how-to-do-camelcase-split-in-python
    return re.sub(r"[-_]", " ", re.sub("(?!^| )([A-Z0-9][a-z0-9]+)", r" \1", identifier))


# TODO: Can I make this part of format_text? Or reuse extract_formatter_and_words?
def formatted_text(formatter):
    def _fmt(m):
        # noinspection PyProtectedMember
        words = parse_words(m)
        tmp = []
        spaces = True
        for i, word in enumerate(words):
            word = parse_word(word)
            smash, func = formatter
            word = func(i, word, i == len(words) - 1)
            spaces = spaces and not smash
            tmp.append(word)
        words = tmp

        sep = " "
        if not spaces:
            sep = ""
        insert(sep.join(words))

    return _fmt


def format_text(m):
    fmt, words = extract_formatter_and_words(m)
    tmp = []
    spaces = True
    for i, word in enumerate(words):
        word = parse_word(word)
        for name in reversed(fmt):
            smash, func = formatters[name]
            word = func(i, word, i == len(words) - 1)
            spaces = spaces and not smash
        tmp.append(word)
    words = tmp

    sep = " "
    if not spaces:
        sep = ""
    insert(sep.join(words))


def extract_formatter_and_words(m):
    fmt = []
    # noinspection PyProtectedMember
    for w in m._words:
        # noinspection PyUnresolvedReferences
        if isinstance(w, Word) and parse_word(w.word) != "over":
            # noinspection PyUnresolvedReferences
            fmt.append(w.word)
    words = [normalize(w) for w in parse_words(m)]
    print(words)
    if not words:
        with clip.capture() as s:
            press("cmd-c", wait=2000)
        try:
            words = normalize(s.get()).split()
        except clip.NoChange:
            words = []
    if not words:
        words = [""]
    return fmt, words


def sponge_format(m):
    _, words = extract_formatter_and_words(m)
    dictation = " ".join(words)
    result = []
    caps = True
    for c in dictation:
        if c == " ":
            result.append(c)
            continue
        result.append(c.upper() if caps else c.lower())
        caps = not caps
    insert("".join(result))


ctx = Context("formatters")
ctx.vocab = vocab + list(jargon_substitutions.keys())
ctx.keymap(
    {
        f"({' | '.join(formatters)})+ [<dgndictation>] [over]": format_text,
        "sponge [<dgndictation>] [over]": sponge_format,
    }
)
