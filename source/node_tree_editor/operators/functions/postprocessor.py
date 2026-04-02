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


def postprocess_ini(op, ini_contents):
    if not ini_contents:
        op.report({"INFO"}, "후처리할 ini_contents가 없습니다")
        return ini_contents

    order = list(ini_contents.get("order", []) or [])
    sections = ini_contents.get("sections", {}) or {}

    # 붕스용 CS 리소스 섹션
    order, sections = _hsr_resource_cs(op, order, sections)

    ini_contents["order"] = order
    ini_contents["sections"] = sections

    return ini_contents
