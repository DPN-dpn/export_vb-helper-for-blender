import os
import re
import bpy

def postprocess_ini(self):
    scene = bpy.context.scene
    export_parent = getattr(scene, "evbh_export_path", "") or ""
    source_mod_path = getattr(scene, "evbh_mod_path", "") or ""

    if not export_parent or not source_mod_path:
        try:
            self.report({"WARNING"}, "내보내기 경로 또는 소스 모드 경로가 설정되지 않아 INI 후처리를 건너뜁니다")
        except Exception:
            pass
        return

    export_dir = os.path.join(export_parent, os.path.basename(os.path.normpath(source_mod_path)))
    if not os.path.isdir(export_dir):
        try:
            self.report({"WARNING"}, f"내보내기 폴더를 찾을 수 없음: {export_dir}")
        except Exception:
            pass
        return

    sec_header_re = re.compile(r"^\s*\[(.*)\]\s*$")
    type_struct_re = re.compile(r"^\s*type\s*=\s*StructuredBuffer\b")
    condition_re = re.compile(r"^(\s*condition\s*=\s*)(.*)$")

    processed = 0
    removed_sections = 0

    for root, dirs, files in os.walk(export_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    raw = f.read()
            except Exception:
                continue

            lines = raw.splitlines()

            # 파싱: 선행 프리앰블과 섹션 단위로 분리
            preamble = []
            sections = []  # list of (header_line, section_name, lines[])
            cur_name = None
            cur_header = None
            cur_lines = []

            for ln in lines:
                m = sec_header_re.match(ln)
                if m:
                    if cur_name is None and cur_lines:
                        preamble = cur_lines
                    elif cur_name is not None:
                        sections.append((cur_header, cur_name, cur_lines))
                    cur_header = ln
                    cur_name = m.group(1)
                    cur_lines = []
                else:
                    cur_lines.append(ln)

            if cur_name is not None:
                sections.append((cur_header, cur_name, cur_lines))
            else:
                if not preamble:
                    preamble = cur_lines

            new_sections = []
            changed = False

            for header, name, s_lines in sections:
                remove_this = False
                # 1) Resource로 시작하고 섹션 내부에 type = StructuredBuffer가 있으면 섹션 삭제
                if name.startswith("Resource"):
                    if any(type_struct_re.match(l) for l in s_lines):
                        remove_this = True

                if remove_this:
                    removed_sections += 1
                    changed = True
                    continue

                # 2) Key로 시작하고 condition = 값에 '='이 포함된 경우 '=' -> '+'로 변경
                if name.startswith("Key"):
                    new_lines = []
                    for l in s_lines:
                        cm = condition_re.match(l)
                        if cm:
                            prefix, val = cm.group(1), cm.group(2)
                            if "=" in val:
                                val = val.replace("=", "+")
                                l = prefix + val
                                changed = True
                        new_lines.append(l)
                    s_lines = new_lines

                new_sections.append((header, name, s_lines))

            if not changed:
                continue

            # 재생성
            out_lines = []
            out_lines.extend(preamble)
            for header, name, s_lines in new_sections:
                out_lines.append(header)
                out_lines.extend(s_lines)

            out_text = "\n".join(out_lines) + "\n"
            try:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(out_text)
                processed += 1
            except Exception:
                try:
                    self.report({"WARNING"}, f"INI 후처리 저장 실패: {fpath}")
                except Exception:
                    pass

    try:
        self.report({"INFO"}, f"INI 후처리 완료: 처리된 파일 {processed}, 제거된 섹션 {removed_sections}")
    except Exception:
        pass