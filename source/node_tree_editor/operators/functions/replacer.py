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

    # 토큰 매핑: 원문(cleaned) -> 토큰, 토큰 -> 최종 문자열(new_cleaned)
    token_for_cleaned = {}
    token_to_final = {}

    op.report(
        {"INFO"}, f"replace_strings 시작: 섹션={len(order)}, 매칭파일={len(matchings)}"
    )

    # 1) filename 라인에서 원문을 토큰으로 바꾸고(원문 -> 토큰), 섹션명 변경대상 수집
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

            # cleaned 문자열에 대한 토큰 생성(이미 있으면 재사용)
            if cleaned not in token_for_cleaned:
                tok = f"__EVBH_FILE_TOKEN_{uuid.uuid4().hex}__"
                token_for_cleaned[cleaned] = tok
                token_to_final[tok] = new_cleaned
            tok = token_for_cleaned[cleaned]

            # 원문 -> 토큰 치환 (주석/뒤따르는 내용 유지)
            new_rest = rest.replace(cleaned, tok, 1)
            new_lines[i] = prefix + new_rest
            modified = True
            file_repl_count += 1

            # 섹션명 변경 규칙 수집 (예약어 보존)
            prefix_found = next(
                (p for p in reserved_prefixes if sec_name.startswith(p)), None
            )
            if prefix_found and new_section_suffix:
                new_sec_name = prefix_found + new_section_suffix
                if new_sec_name != sec_name:
                    section_renames[sec_name] = new_sec_name

        if modified:
            sections[sec_name] = new_lines

    # 2) 모든 토큰 -> 최종 문자열 치환 (토큰화로 인한 충돌 방지 후 최종 적용)
    if token_to_final:
        for sn, lines in sections.items():
            for i, ln in enumerate(lines):
                new_ln = ln
                for tok, final in token_to_final.items():
                    if tok in new_ln:
                        new_ln = new_ln.replace(tok, final)
                if new_ln != ln:
                    lines[i] = new_ln
            sections[sn] = lines

    # 3) 섹션명 변경 처리 (기존 로직 유지)
    if section_renames:
        token_for_old = {
            old: f"__EVBH_SEC_TOKEN_{uuid.uuid4().hex}__"
            for old in section_renames.keys()
        }

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

        # 키(섹션명) 교체 및 순서 재구성
        new_sections = {}
        new_order = []
        for nm in order:
            target = section_renames.get(nm, nm)
            if target in new_sections:
                new_sections[target] = sections.get(nm, []) or []
                if target in new_order:
                    try:
                        new_order.remove(target)
                    except ValueError:
                        pass
                new_order.append(target)
            else:
                new_sections[target] = sections.get(nm, []) or []
                new_order.append(target)

        ini_contents["order"] = new_order
        ini_contents["sections"] = new_sections
    else:
        ini_contents["sections"] = sections

    op.report({"INFO"}, f"ini 내용 문자열 치환 완료 (파일 치환: {file_repl_count}개)")
    return ini_contents
