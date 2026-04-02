import re
import os
import uuid

def replace_strings(op, ini_contents, matchings):
    """
    sections: {'order': [...], 'sections': {name: [lines]}}
    matchings: {mod_name: {'sockets': set([...]), 'replacements': {orig: {'new_base':..., 'section':...}}}}
    함수는 ini_contents를 제자리에서 수정하고 최종 ini_contents를 반환합니다.
    """
    if not ini_contents or not matchings:
        op.report({"INFO"}, "replace_strings: 치환할 데이터 없음")
        return ini_contents

    order = list(ini_contents.get("order", []) or [])
    sections = ini_contents.get("sections", {}) or {}

    filename_re = re.compile(r"^\s*(filename\s*=\s*)(.+)$", re.IGNORECASE)
    reserved_prefixes = (
        "Resource",
        "TextureOverride",
        "CommandList",
        "Key",
        "ShaderOverride",
        "CustomShader",
    )

    section_renames = {}
    file_repl_count = 0

    op.report({"INFO"}, f"replace_strings 시작: 섹션={len(order)}, 매칭파일={len(matchings)}")

    # 1) 각 섹션의 filename 값 교체하고, 섹션명 변경 대상 수집
    for sec_name in list(order):
        lines = sections.get(sec_name, []) or []
        new_lines = list(lines)
        modified = False
        for i, ln in enumerate(lines):
            m = filename_re.match(ln)
            if not m:
                continue
            prefix = m.group(1)
            rest = m.group(2)

            cleaned = re.split(r";|#", rest)[0].strip()
            if not cleaned:
                continue

            quote = ""
            inner = cleaned
            if (inner.startswith('"') and inner.endswith('"')) or (
                inner.startswith("'") and inner.endswith("'")
            ):
                quote = inner[0]
                inner = inner[1:-1]

            val_base = os.path.basename(inner)

            found_repl = None
            for mod_name, mobj in (matchings or {}).items():
                sockets = mobj.get("sockets") or set()
                repls = mobj.get("replacements") or {}
                for orig in sockets:
                    if not orig:
                        continue
                    orig_base = os.path.basename(orig)
                    if not orig_base:
                        continue
                    if (
                        orig_base == val_base
                        or orig_base in val_base
                        or orig in inner
                        or orig.replace("\\", "/") in inner
                    ):
                        found_repl = repls.get(orig) or repls.get(orig_base)
                        if found_repl:
                            break
                if found_repl:
                    break

            if not found_repl:
                continue

            new_base = found_repl.get("new_base")
            new_section_suffix = found_repl.get("section")
            if not new_base:
                continue

            new_cleaned = f"{quote}{new_base}{quote}" if quote else new_base
            new_rest = rest.replace(cleaned, new_cleaned, 1)
            new_lines[i] = prefix + new_rest
            modified = True
            file_repl_count += 1

            # 섹션명 교체 규칙 적용 (예약어 보존)
            prefix_found = next((p for p in reserved_prefixes if sec_name.startswith(p)), None)
            if prefix_found and new_section_suffix:
                new_sec_name = prefix_found + new_section_suffix
                if new_sec_name != sec_name:
                    section_renames[sec_name] = new_sec_name

        if modified:
            sections[sec_name] = new_lines

    # 2) 섹션명 변경이 있으면, 섹션 참조들까지 안전하게 교체하고 키 이름 갱신
    if section_renames:
        token_for_old = {old: f"__EVBH_SEC_TOKEN_{uuid.uuid4().hex}__" for old in section_renames.keys()}

        # old -> token
        for sn, lines in sections.items():
            for i, ln in enumerate(lines):
                new_ln = ln
                for old, tok in token_for_old.items():
                    if old in new_ln:
                        new_ln = new_ln.replace(old, tok)
                if new_ln != ln:
                    lines[i] = new_ln
            sections[sn] = lines

        # token -> final new name
        for sn, lines in sections.items():
            for i, ln in enumerate(lines):
                new_ln = ln
                for old, tok in token_for_old.items():
                    if tok in new_ln:
                        new_ln = new_ln.replace(tok, section_renames[old])
                if new_ln != ln:
                    lines[i] = new_ln
            sections[sn] = lines

        # 키(섹션명) 교체 및 순서 재구성 (충돌 시 고유명 생성)
        new_sections = {}
        new_order = []
        used = set()
        for nm in order:
            target = section_renames.get(nm, nm)
            unique = target
            if unique in used:
                base = target
                idx = 1
                while True:
                    candidate = f"{base}_{idx}"
                    if candidate not in used:
                        unique = candidate
                        break
                    idx += 1
            new_sections[unique] = sections.get(nm, []) or []
            new_order.append(unique)
            used.add(unique)

        ini_contents["order"] = new_order
        ini_contents["sections"] = new_sections
    else:
        ini_contents["sections"] = sections

    op.report({"INFO"}, f"ini 내용 문자열 치환 완료")
    return ini_contents