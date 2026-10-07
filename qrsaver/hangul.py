"""QR 스캐너 입력 보정.

QR 스캐너는 키보드처럼 동작하므로 한/영 상태가 '한글'이면
'26-C -053637' 이 '26-ㅊ -053637' 처럼 들어온다. 두벌식 자판 기준으로
한글을 원래 영문 키로 되돌린다.
"""
import re

_CHO = ["r", "R", "s", "e", "E", "f", "a", "q", "Q", "t", "T", "d", "w", "W",
        "c", "z", "x", "v", "g"]
_JUNG = ["k", "o", "i", "O", "j", "p", "u", "P", "h", "hk", "ho", "hl", "y",
         "n", "nj", "np", "nl", "b", "m", "ml", "l"]
_JONG = ["", "r", "R", "rt", "s", "sw", "sg", "e", "f", "fr", "fa", "fq", "ft",
         "fx", "fv", "fg", "a", "q", "qt", "t", "T", "d", "w", "c", "z", "x",
         "v", "g"]
# 호환 자모 U+3131(ㄱ) ~ U+3163(ㅣ)
_COMPAT = ("r R rt s sw sg e E f fr fa fq ft fx fv fg a q Q qt t T d w W c z x v g "
           "k o i O j p u P h hk ho hl y n nj np nl b m ml l").split()


def hangul_to_qwerty(text):
    out = []
    for ch in text:
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            idx = code - 0xAC00
            out.append(_CHO[idx // 588] + _JUNG[(idx % 588) // 28] + _JONG[idx % 28])
        elif 0x3131 <= code <= 0x3163:
            out.append(_COMPAT[code - 0x3131])
        else:
            out.append(ch)
    return "".join(out)


_AMIS_RE = re.compile(r"^(\d{2})-([A-Za-z]{1,2})\s*-\s*(\d{3,})$")


def amis_format(code):
    """검사번호를 AMIS 화면 표기로 통일: '26-S-082711' / '26-S  - 082711' → '26-S -082711'.
    형식이 다르면 그대로 둔다."""
    m = _AMIS_RE.match((code or "").strip())
    if not m:
        return code
    return "%s-%s -%s" % (m.group(1), m.group(2).upper(), m.group(3))


def normalize_code(raw, fix_hangul=True, uppercase=True, amis_space=True):
    """스캔된 문자열을 검사번호로 정리 (앞뒤 공백/개행 제거).
    amis_space=True 면 QR 의 '26-S-082711' 을 AMIS 표기 '26-S -082711' 로 바꾼다."""
    code = raw.replace("\r", "").replace("\n", "").replace("\t", "").strip()
    if fix_hangul:
        code = hangul_to_qwerty(code)
    if uppercase:
        code = code.upper()
    if amis_space:
        code = amis_format(code)
    return code


_PATTERN = re.compile(r"^\d{2}-[A-Z]{1,2}\s*-\s*\d{3,}$")


def looks_like_accession(code):
    """'26-C -053637' 같은 검사번호 형식인지 (경고 표시용)."""
    return bool(_PATTERN.match(code))
