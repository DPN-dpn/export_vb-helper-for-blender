import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper
import os
import re
import shutil
from .functions import ini_parser, collector, replacer, postprocessor, run_export_vb


def select_export_path(context, path: str) -> str:
    chosen = os.path.expanduser(path or "")
    if os.path.isfile(chosen):
        base = os.path.dirname(chosen)
    else:
        base = chosen
    if not base or not os.path.isdir(base):
        raise ValueError(f"유효하지 않은 폴더입니다: {base}")
    # 선택은 내보내기 대상 폴더를 지정하므로 evbh_export_path에 저장
    context.scene.evbh_export_path = base
    return base


def create_ini_contents(op, need_sockets):
    # need_sockets를 바탕으로 데이터 블록에 있는 ini에서 섹션을 긁어옴
    # 반환: (new_order, {name: lines})
    new_sections = {}
    new_order = []

    for mod_name, sockets in (need_sockets or {}).items():
        # 텍스트 블록 찾기(역슬래시/슬래시 변환 허용)
        text = bpy.data.texts.get(mod_name)
        if text is None:
            text = bpy.data.texts.get(mod_name.replace("\\", "/"))
        if text is None:
            op.report({"WARNING"}, f"텍스트 데이터 블록을 찾지 못함: {mod_name}")
            continue

        order, sections = ini_parser.parse_ini(text)

        # 초기: Resource로 시작하는 섹션 중 filename= 값에 소켓이 포함된 섹션 수집
        initial = set()
        filename_re = re.compile(r"^\s*filename\s*=\s*(.+)$", re.IGNORECASE)
        for sec_name in order:
            if not sec_name.lower().startswith("resource"):
                continue
            lines = sections.get(sec_name, []) or []
            for ln in lines:
                m = filename_re.match(ln)
                if not m:
                    continue
                val = m.group(1).strip()
                val = re.split(r";|#", val)[0].strip().strip('"').strip("'")
                val_base = os.path.basename(val)
                for s in sockets:
                    if not s:
                        continue
                    s_base = os.path.basename(s)
                    if s_base and (
                        s_base == val_base
                        or s_base in val_base
                        or s in val
                        or s.replace("\\", "/") in val
                    ):
                        initial.add(sec_name)
                        break
                if sec_name in initial:
                    break

        # 재귀적 참조: 초기 섹션명을 값으로 참조하는 섹션들을 전부 포함
        found = set(initial)
        changed = True
        kv_re = re.compile(r"^(?P<k>[^=]+)=(?P<v>.+)$")
        while changed:
            changed = False
            for sec_name, lines in sections.items():
                if sec_name in found:
                    continue
                for ln in lines or []:
                    m = kv_re.match(ln)
                    if not m:
                        continue
                    v = m.group("v").strip()
                    v_clean = re.split(r";|#", v)[0].strip().strip('"').strip("'")
                    if v_clean in found:
                        found.add(sec_name)
                        changed = True
                        break
                if changed:
                    break

        # 원래 순서를 유지하여 new_sections/new_order에 추가
        for nm in order:
            if nm in found and nm not in new_sections:
                new_sections[nm] = sections.get(nm, []) or []
                new_order.append(nm)

    ini_contents = {
        "order": new_order,
        "sections": new_sections,
    }

    return ini_contents


def create_exported_folder(op, export_parent, mod_path):
    # 내보내기 폴더 생성: {export_parent}/{mod_name}
    export_dir = os.path.join(
        export_parent, os.path.basename(os.path.normpath(mod_path))
    )
    try:
        os.makedirs(export_dir, exist_ok=True)
    except Exception as e:
        raise op.report({"ERROR"}, f"내보내기 폴더 생성 실패: {export_dir} ({e})")
    return export_dir


def copy_exported_files(op, export_dir, mod_path, matchings):
    if not matchings:
        op.report({"INFO"}, "복사할 매칭 정보가 없습니다")
        return []

    os.makedirs(export_dir, exist_ok=True)

    copied_files = []
    used_names = set()

    for mod_name, m in (matchings or {}).items():
        sockets = m.get("sockets") or set()
        replacements = m.get("replacements") or {}
        # 모드 파일 기준 디렉터리
        mod_full = os.path.normpath(os.path.join(mod_path, mod_name))
        mod_dir = os.path.dirname(mod_full) or mod_path

        for orig in list(sockets):
            if not orig:
                continue
            orig_base = os.path.basename(orig)

            # 1) 원본 파일 경로 결정
            src = os.path.normpath(os.path.join(mod_dir, orig))
            if not os.path.isfile(src):
                if os.path.isabs(orig) and os.path.isfile(orig):
                    src = orig
                else:
                    found = None
                    for root, _, files in os.walk(mod_dir):
                        if orig_base in files:
                            found = os.path.join(root, orig_base)
                            break
                    if not found:
                        for root, _, files in os.walk(mod_path):
                            if orig_base in files:
                                found = os.path.join(root, orig_base)
                                break
                    if found:
                        src = found
                    else:
                        op.report(
                            {"WARNING"},
                            f"복사할 파일을 찾지 못함: {orig} (mod: {mod_name})",
                        )
                        continue

            # 2) 목표 파일명 결정 (replacements에서 new_base 사용)
            if orig in replacements:
                repl_key = orig
            elif orig_base in replacements:
                repl_key = orig_base
            else:
                repl_key = orig
                replacements.setdefault(repl_key, {})["new_base"] = orig_base

            desired_base = replacements.get(repl_key, {}).get("new_base") or orig_base

            # 충돌 시 덮어쓰기
            candidate = desired_base
            dst_path = os.path.join(export_dir, candidate)
            if candidate in used_names or os.path.exists(dst_path):
                op.report(
                    {"INFO"},
                    f"파일명 충돌로 덮어쓰기: '{candidate}' (mod: {mod_name})",
                )

            dst = os.path.join(export_dir, candidate)
            dst_dir = os.path.dirname(dst)
            if dst_dir:
                os.makedirs(dst_dir, exist_ok=True)

            try:
                shutil.copy2(src, dst)
                copied_files.append(dst)
                used_names.add(candidate)
                # matchings에 최종 파일명 기록 (나중에 INI 작성 시 사용)
                replacements.setdefault(repl_key, {})["final_base"] = candidate
            except Exception as e:
                op.report(
                    {"WARNING"},
                    f"파일 복사 실패: {src} -> {dst} ({e})",
                )
                continue

    op.report({"INFO"}, f"파일 복사 완료: {len(copied_files)}개")
    return copied_files


def write_ini_file(op, export_dir, ini_contents, asset_name):
    if not ini_contents:
        op.report({"INFO"}, "작성할 ini가 없습니다")
        return None

    os.makedirs(export_dir, exist_ok=True)

    order = list(ini_contents.get("order", []) or [])
    sections = ini_contents.get("sections", {}) or {}

    try:
        ini_text = ini_parser.unparse_ini(order, sections)
    except Exception as e:
        op.report({"WARNING"}, f"INI 직렬화 실패: {e}")
        return None

    ini_fname = f"{asset_name}.ini" if asset_name else "exported.ini"
    out_path = os.path.join(export_dir, ini_fname)

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(ini_text)
        in_mem = globals().get("_IN_MEMORY_INIS")
        if isinstance(in_mem, dict):
            in_mem[out_path] = ini_text
        op.report({"INFO"}, f"INI 파일 작성: {out_path}")
        return out_path
    except Exception as e:
        op.report({"WARNING"}, f"INI 파일 쓰기 실패: {out_path} ({e})")
        return None


def create_exported_files(
    op, export_parent, mod_path, ini_contents, matchings, asset_name
):
    # 내보내기 폴더 생성
    export_dir = create_exported_folder(op, export_parent, mod_path)

    # 파일 복사, 파일명 변경
    copy_exported_files(op, export_dir, mod_path, matchings)

    # ini 작성
    write_ini_file(op, export_dir, ini_contents, asset_name)

    return export_dir


class EVHB_OT_export_mod(Operator, ImportHelper):
    bl_idname = "evhb.export_mod"
    bl_label = "내보내기"
    bl_description = "사전작업을 적용한 모드를 내보냅니다"

    filename_ext = ""
    filter_glob: StringProperty(default="", options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        # 내보내기 경로 설정
        try:
            export_path = select_export_path(context, self.filepath)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        # 모드 폴더 경로
        mod_path = getattr(context.scene, "evbh_current_mod_path", "")
        if not mod_path or not os.path.isdir(mod_path):
            self.report({"ERROR"}, "모드 폴더가 유효하지 않습니다: " + mod_path)
            return {"CANCELLED"}

        # 에셋 경로
        asset_path = getattr(context.scene, "evbh_current_asset_path", "")
        if not asset_path or not os.path.isfile(asset_path):
            self.report({"ERROR"}, "에셋 파일이 유효하지 않습니다: " + asset_path)
            return {"CANCELLED"}

        # 현재 노드트리 얻기
        tree = getattr(context.space_data, "node_tree", None)
        mappings = collector.collect_result_mappings(
            tree, os.path.basename(os.path.dirname(asset_path))
        )

        # 내보내기에 필요한 소켓만 구분
        need_sockets = collector.collect_need_sockets(mappings)

        # 연결된 소켓이 없으면 종료
        if not need_sockets:
            self.report({"INFO"}, "내보낼 소켓이 없습니다")
            return {"FINISHED"}

        # 새로 생성될 ini 내용 모으기
        ini_contents = create_ini_contents(self, need_sockets)

        # 교체할 문자열 매칭 모으기
        matchings, asset_name = collector.collect_matching_strings(mappings)

        # ini 문자열 교체
        ini_contents = replacer.replace_strings(self, ini_contents, matchings)

        # ini 후처리
        ini_contents = postprocessor.postprocess_ini(self, ini_contents)

        # 내보내기 파일 생성 (matchings 사용해서 파일명 변경도 처리)
        export_dir = create_exported_files(
            self, export_path, mod_path, ini_contents, matchings, asset_name
        )

        # 엵툵 내보내기
        from ...core.preferences import addon_module_name

        prefs = bpy.context.preferences.addons[addon_module_name()].preferences
        if prefs.evbh_export_vb_use and prefs.evbh_export_vb:
            run_export_vb.run_export_vb(
                self, prefs.evbh_export_vb, export_dir, asset_path
            )

        return {"FINISHED"}


classes = (EVHB_OT_export_mod,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
