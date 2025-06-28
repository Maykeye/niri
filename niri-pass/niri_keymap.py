def keys(n: list[int]):
    arr = []
    for j in n:
        arr.append(f"+{j}")
    for j in reversed(n):
        arr.append(f"-{j}")
    return " ".join(arr)


def keymap():
    keymap = {}

    for i, (nonshift, shift) in enumerate(zip("1234567890", "!@#$%^&*()")):
        keymap[nonshift] = keys([10 + i])
        keymap[shift] = keys([50, 10 + i])
    for i, key in enumerate("qwertyuiop"):
        keymap[key] = keys([24 + i])
        keymap[key.upper()] = keys([50, 24 + i])
    for i, key in enumerate("asdfghjkl"):
        keymap[key] = keys([38 + i])
        keymap[key.upper()] = keys([50, 38 + i])
    for i, key in enumerate("zxcvbnm"):
        keymap[key] = keys([52 + i])
        keymap[key.upper()] = keys([50, 52 + i])

    keymap["-"] = keys([20])
    keymap["="] = keys([21])
    keymap["["] = keys([34])
    keymap["]"] = keys([35])
    keymap[";"] = keys([47])
    keymap["'"] = keys([48])
    keymap["`"] = keys([49])
    keymap[","] = keys([59])
    keymap["."] = keys([60])
    keymap["/"] = keys([61])
    keymap[" "] = keys([65])
    keymap["_"] = keys([50, 20])
    keymap["+"] = keys([50, 21])
    keymap["{"] = keys([50, 34])
    keymap["}"] = keys([50, 35])
    keymap[":"] = keys([50, 47])
    keymap['"'] = keys([50, 48])
    keymap["~"] = keys([50, 49])
    keymap["\\"] = keys([51])
    keymap["|"] = keys([50, 51])
    keymap["<"] = keys([50, 59])
    keymap[">"] = keys([50, 60])
    keymap["?"] = keys([50, 61])
    return keymap


def encode_string(s: str):
    res = []
    k = keymap()
    for ch in s:
        if ch not in k:
            raise ValueError(f"Char {ch} is not mapped")
        res.append(k[ch])
    return " ".join(res)
