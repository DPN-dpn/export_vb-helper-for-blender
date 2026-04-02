import re


def parse_ini(text):
    """텍스트 블록 또는 일반 문자열을 섹션 단위로 파싱: (order, {name: lines}) 반환"""
    if hasattr(text, "lines"):
        raw_lines = [l.body for l in text.lines]
    else:
        raw_lines = text.splitlines(True)

    sections = {}
    order = []
    cur_name = None
    cur_lines = []

    for raw in raw_lines:
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^\[(.+?)\]$", line)
        if m:
            if cur_name is not None:
                sections[cur_name] = cur_lines
            cur_name = m.group(1)
            order.append(cur_name)
            cur_lines = []
            continue
        if cur_name is None:
            continue
        cur_lines.append(line)

    if cur_name is not None:
        sections[cur_name] = cur_lines

    return order, sections


def unparse_ini(order, sections=None) -> str:
    """
    parse_ini의 역함수.
    사용법:
      - unparse_ini((order, sections))
      - unparse_ini(order, sections)
    반환: INI 파일 내용 (문자열, 각 라인은 '\\n'으로 끝남)
    """
    # flexible input: single tuple거나 (order, sections) 형태 또는 두 인자 형태 지원
    if sections is None:
        try:
            order, sections = order
        except Exception as e:
            raise TypeError(
                "unparse_ini은 (order, sections) 튜플 또는 order, sections 두 인자를 받습니다"
            ) from e

    if order is None:
        order = list(sections.keys())

    out_lines = []
    for sec in order:
        if sec not in sections:
            continue
        out_lines.append(f"[{sec}]")
        for ln in sections.get(sec, []):
            if ln is None:
                continue
            s = str(ln).rstrip("\r\n")
            out_lines.append(s)

    return ("\n".join(out_lines) + "\n") if out_lines else ""
