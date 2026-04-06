import re


def _hsr_resource_cs(op, order, sections):
    """
    - order: 섹션명 리스트
    - sections: {name: [lines]}
    Resource로 시작하는 섹션 중 내부에 "type = StructuredBuffer"가 있으면 해당 섹션만 제거.
    """
    type_struct_re = re.compile(r"^\s*type\s*=\s*StructuredBuffer\b", re.IGNORECASE)

    removed = []
    for sec_name in list(order):
        if not sec_name.startswith("Resource"):
            continue
        lines = sections.get(sec_name, []) or []
        if any(type_struct_re.match(l) for l in lines if l):
            removed.append(sec_name)
            sections.pop(sec_name, None)

    if removed:
        new_order = [nm for nm in order if nm not in removed]
        order = new_order
        op.report(
            {"INFO"},
            f"CS 리소스 섹션 제거 완료: 제거된 섹션 {len(removed)}개 - {', '.join(removed)}",
        )

    return order, sections


def _replace_relational_logic(op, order, sections):
    """
    섹션 내부의 비교 연산자 치환:
    - A != B -> (A > B || A < B)
    - A >= B -> (A > B || A == B)
    - A <= B -> (A < B || A == B)

    인용부("...")와 주석(선행 ';') 내의 내용은 변경하지 않습니다.
    """
    pattern_ne = re.compile(r"(\S+)\s*!=\s*(\S+)")
    pattern_ge = re.compile(r"(\S+)\s*>=\s*(\S+)")
    pattern_le = re.compile(r"(\S+)\s*<=\s*(\S+)")

    def _outside_quotes(s, pos):
        return (s.count('"', 0, pos) % 2 == 0) and (s.count("'", 0, pos) % 2 == 0)

    def _safe_replace(pattern, text, repl_func):
        last = 0
        out = []
        count = 0
        for m in pattern.finditer(text):
            if not _outside_quotes(text, m.start()):
                continue
            out.append(text[last : m.start()])
            out.append(repl_func(m))
            last = m.end()
            count += 1
        out.append(text[last:])
        return "".join(out), count

    total_ne = total_ge = total_le = 0
    new_sections = {}

    for sec_name, lines in sections.items():
        if not lines:
            new_sections[sec_name] = lines
            continue

        updated_lines = []
        for line in lines:
            ln = line

            # 주석 라인은 변경하지 않음
            if ln.strip().startswith(";"):
                updated_lines.append(ln)
                continue

            # 순서: >=, <=, != (중첩 방지 및 가독성)
            ln, cge = _safe_replace(
                pattern_ge,
                ln,
                lambda m: f"({m.group(1)} > {m.group(2)} || {m.group(1)} == {m.group(2)})",
            )
            ln, cle = _safe_replace(
                pattern_le,
                ln,
                lambda m: f"({m.group(1)} < {m.group(2)} || {m.group(1)} == {m.group(2)})",
            )
            ln, cne = _safe_replace(
                pattern_ne,
                ln,
                lambda m: f"({m.group(1)} > {m.group(2)} || {m.group(1)} < {m.group(2)})",
            )

            total_ge += cge
            total_le += cle
            total_ne += cne

            updated_lines.append(ln)

        new_sections[sec_name] = updated_lines

    if (total_ne + total_ge + total_le) > 0:
        sections = new_sections
        op.report(
            {"INFO"},
            f"연산자 치환 완료: != {total_ne}개, >= {total_ge}개, <= {total_le}개",
        )

    return order, sections


def preprocess_ini(op, ini_contents):
    if not ini_contents:
        op.report({"INFO"}, "전처리할 ini_contents가 없습니다")
        return ini_contents

    order = list(ini_contents.get("order", []) or [])
    sections = ini_contents.get("sections", {}) or {}

    # 붕스용 CS 리소스 섹션
    order, sections = _hsr_resource_cs(op, order, sections)

    # !=, >=, <= 연산자 치환
    order, sections = _replace_relational_logic(op, order, sections)

    ini_contents["order"] = order
    ini_contents["sections"] = sections

    return ini_contents
