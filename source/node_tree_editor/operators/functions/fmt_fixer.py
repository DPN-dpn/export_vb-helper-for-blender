import os
import re
import shutil

# DXGI 포맷 → 바이트 크기 (DXGI_FORMAT_ 접두어 제거 후 대문자 키)
_FORMAT_BYTE_SIZES = {
    "R32G32B32A32_FLOAT": 16, "R32G32B32A32_UINT": 16, "R32G32B32A32_SINT": 16,
    "R32G32B32_FLOAT": 12,   "R32G32B32_UINT": 12,   "R32G32B32_SINT": 12,
    "R32G32_FLOAT": 8,       "R32G32_UINT": 8,        "R32G32_SINT": 8,
    "R32_FLOAT": 4,          "R32_UINT": 4,           "R32_SINT": 4,
    "R16G16B16A16_FLOAT": 8, "R16G16B16A16_UINT": 8,  "R16G16B16A16_SINT": 8,
    "R16G16B16A16_UNORM": 8, "R16G16B16A16_SNORM": 8,
    "R16G16_FLOAT": 4,       "R16G16_UINT": 4,        "R16G16_SINT": 4,
    "R16G16_UNORM": 4,       "R16G16_SNORM": 4,
    "R16_FLOAT": 2,          "R16_UINT": 2,           "R16_SINT": 2,
    "R16_UNORM": 2,          "R16_SNORM": 2,
    "R8G8B8A8_UNORM": 4,     "R8G8B8A8_UINT": 4,      "R8G8B8A8_SINT": 4,
    "R8G8B8A8_SNORM": 4,     "B8G8R8A8_UNORM": 4,
    "R8G8_UNORM": 2,         "R8G8_UINT": 2,          "R8G8_SINT": 2,
    "R8G8_SNORM": 2,
    "R8_UNORM": 1,           "R8_UINT": 1,            "R8_SINT": 1,
    "R8_SNORM": 1,
}

_STRIDE_RE = re.compile(r"^\s*stride\s*:\s*(\d+)", re.IGNORECASE)
_OFFSET_RE = re.compile(r"^\s*AlignedByteOffset\s*:\s*(\d+)", re.IGNORECASE)
_FORMAT_RE = re.compile(r"^\s*Format\s*:\s*(.+)$", re.IGNORECASE)
_VDATA_RE  = re.compile(r"^\s*vertex-data\s*:", re.IGNORECASE)

# ini buf stride 수정용 정규식
_STRIDE_INI_RE   = re.compile(r"^(\s*stride\s*=\s*)(\d+)", re.IGNORECASE)
_FILENAME_INI_RE = re.compile(r"^\s*filename\s*=\s*(.+)", re.IGNORECASE)


def _format_byte_size(fmt_str):
    key = fmt_str.strip().upper().replace("DXGI_FORMAT_", "")
    return _FORMAT_BYTE_SIZES.get(key)


def check_and_fix_fmt_stride(path):
    """
    .fmt 파일(또는 vb 텍스트 덤프)의 stride 값을 검사하고, 잘못된 경우 수정합니다.

    stride의 올바른 값 = 마지막 element의 AlignedByteOffset + 해당 Format의 바이트 크기

    Returns:
        (fixed: bool, old_stride: int | None, new_stride: int | None, reason: str)
        - fixed=True  : 파일을 수정함
        - fixed=False : 수정 불필요하거나 수정 불가
    """
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return False, None, None, f"파일 읽기 실패: {e}"

    stride = None
    stride_line_idx = None
    last_offset = None
    last_format = None

    for i, line in enumerate(lines):
        # vertex-data: 이후는 헤더가 아니므로 중단
        if _VDATA_RE.match(line):
            break
        m = _STRIDE_RE.match(line)
        if m:
            stride = int(m.group(1))
            stride_line_idx = i
            continue
        m = _OFFSET_RE.match(line)
        if m:
            last_offset = int(m.group(1))
            continue
        m = _FORMAT_RE.match(line)
        if m:
            last_format = m.group(1).strip()

    if stride is None or stride_line_idx is None:
        return False, None, None, "stride 항목 없음"
    if last_offset is None or last_format is None:
        return False, stride, stride, "element 정보 없음"

    fmt_size = _format_byte_size(last_format)
    if fmt_size is None:
        return False, stride, stride, f"알 수 없는 포맷: {last_format}"

    correct_stride = last_offset + fmt_size
    if stride == correct_stride:
        return False, stride, correct_stride, "이상 없음"

    # stride 수정 (들여쓰기 보존)
    orig_line = lines[stride_line_idx]
    leading = orig_line[: len(orig_line) - len(orig_line.lstrip())]
    lines[stride_line_idx] = f"{leading}stride: {correct_stride}\n"

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        return False, stride, correct_stride, f"파일 쓰기 실패: {e}"

    return True, stride, correct_stride, "수정 완료"


def copy_and_fix_fmt_files(op, src_dir, dst_dir):
    """
    src_dir 내의 모든 .fmt 파일을 dst_dir에 복사한 뒤 stride 오류를 수정합니다.
    원본(src_dir)은 변경하지 않습니다.

    Returns: 수정된 파일 수
    """
    if not src_dir or not os.path.isdir(src_dir):
        return 0

    fixed_count = 0

    for root, _, files in os.walk(src_dir):
        for fname in files:
            if not fname.lower().endswith(".fmt"):
                continue

            src_path = os.path.join(root, fname)
            try:
                rel = os.path.relpath(root, src_dir)
            except ValueError:
                continue

            dest_subdir = os.path.join(dst_dir, rel) if rel != "." else dst_dir
            os.makedirs(dest_subdir, exist_ok=True)
            dst_path = os.path.join(dest_subdir, fname)

            try:
                shutil.copy2(src_path, dst_path)
            except Exception as e:
                op.report({"WARNING"}, f"[fmt] 복사 실패: {fname} ({e})")
                continue

            fixed, old_s, new_s, reason = check_and_fix_fmt_stride(dst_path)
            if fixed:
                fixed_count += 1
                op.report(
                    {"INFO"},
                    f"[fmt stride 수정] {fname}: {old_s} → {new_s}",
                )
            elif reason not in ("이상 없음", "stride 항목 없음", "element 정보 없음"):
                op.report({"WARNING"}, f"[fmt stride 검사] {fname}: {reason}")

    return fixed_count


def fix_fmt_files_inplace(op, directory):
    """
    directory 내의 모든 .fmt 파일을 그 자리에서 stride 오류 수정합니다.
    (파일 복사 없이 직접 수정)

    Returns: 수정된 파일 수
    """
    if not directory or not os.path.isdir(directory):
        return 0

    fixed_count = 0

    for root, _, files in os.walk(directory):
        for fname in files:
            if not fname.lower().endswith(".fmt"):
                continue

            path = os.path.join(root, fname)
            fixed, old_s, new_s, reason = check_and_fix_fmt_stride(path)
            if fixed:
                fixed_count += 1
                op.report(
                    {"INFO"},
                    f"[fmt stride 수정] {fname}: {old_s} → {new_s}",
                )
            elif reason not in ("이상 없음", "stride 항목 없음", "element 정보 없음"):
                op.report({"WARNING"}, f"[fmt stride 검사] {fname}: {reason}")

    return fixed_count


# ---------------------------------------------------------------------------
# ini Resource stride 사전 수정 (export_vb 실행 전 호출)
# vb0 txt의 element 정의에서 버퍼별 stride를 직접 계산하는 방식 사용
# ---------------------------------------------------------------------------

# SemanticName → 버퍼 타입 매핑 (ZZZ/HSR/Genshin 표준 3-버퍼 구조)
_SEMANTIC_TO_BUF = {
    "POSITION":     "Position",
    "NORMAL":       "Position",
    "TANGENT":      "Position",
    "BLENDWEIGHTS": "Blend",
    "BLENDWEIGHT":  "Blend",
    "BLENDINDICES": "Blend",
    "BLENDINDEX":   "Blend",
    # COLOR, TEXCOORD* → "Texcoord" (기본값)
}

_SEMANTIC_NAME_RE = re.compile(r"^\s*SemanticName\s*:\s*(.+)$", re.IGNORECASE)


def _parse_buffer_strides_from_vb0(vb0_path):
    """vb0 txt element 정의에서 {"Position": N, "Blend": N, "Texcoord": N} 반환"""
    strides = {"Position": 0, "Blend": 0, "Texcoord": 0}
    current_semantic = None
    try:
        with open(vb0_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if _VDATA_RE.match(line):
                    break
                m = _SEMANTIC_NAME_RE.match(line)
                if m:
                    current_semantic = m.group(1).strip().upper()
                    continue
                m = _FORMAT_RE.match(line)
                if m and current_semantic is not None:
                    size = _format_byte_size(m.group(1).strip())
                    if size:
                        buf_type = _SEMANTIC_TO_BUF.get(current_semantic, "Texcoord")
                        strides[buf_type] += size
                    current_semantic = None
    except Exception:
        return {}
    return {k: v for k, v in strides.items() if v > 0}


def _collect_vb0_strides(asset_dir):
    """
    asset_dir 안의 vb0 txt 파일들을 읽어
    {캐릭터명: {"Position": N, "Blend": N, "Texcoord": N}} 반환
    예) "BelleSummerBodyA-vb0=b95ddd01.txt" → {"BelleSummerBodyA": {Position:40, Blend:32, Texcoord:24}}
    """
    result = {}
    if not asset_dir or not os.path.isdir(asset_dir):
        return result
    for root, _, files in os.walk(asset_dir):
        for fname in files:
            if not (fname.endswith(".txt") and "vb0" in fname):
                continue
            strides = _parse_buffer_strides_from_vb0(os.path.join(root, fname))
            if strides:
                result[fname.split("-")[0]] = strides
    return result


def _fix_ini_strides_by_vb0(op, ini_path, mesh_strides_map):
    """
    ini의 Resource 섹션 이름에서 Position/Blend/Texcoord 타입과
    메시명을 파악해 vb0 기반의 올바른 stride로 수정합니다.
    """
    try:
        with open(ini_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        op.report({"WARNING"}, f"[ini stride] 읽기 실패: {ini_path} ({e})")
        return 0

    in_resource = False
    section_buf_type = None
    section_mesh_key = None
    stride_line_idx = None
    stride_value = None
    changes = []

    def flush_section():
        nonlocal stride_line_idx, stride_value, section_buf_type, section_mesh_key
        if (
            in_resource
            and section_buf_type
            and section_mesh_key
            and stride_line_idx is not None
        ):
            correct = mesh_strides_map.get(section_mesh_key, {}).get(section_buf_type)
            if correct and correct != stride_value:
                changes.append((stride_line_idx, correct, stride_value))
        stride_line_idx = None
        stride_value = None
        section_buf_type = None
        section_mesh_key = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            flush_section()
            end = stripped.find("]")
            sec_name = stripped[1:end] if end > 0 else stripped[1:]
            in_resource = sec_name.lower().startswith("resource")
            if in_resource:
                # 버퍼 타입 판별 (Texcoord를 먼저 체크해 오탐 방지)
                section_buf_type = None
                for buf in ("Texcoord", "Blend", "Position"):
                    if buf in sec_name:
                        section_buf_type = buf
                        break
                # 메시 키 판별: "Resource" + buf_type 제거 후 vb0 키와 매칭
                # 예) "ResourceBelleSummerBodyTexcoord" → mesh_name_part = "BelleSummerBody"
                # vb0 키 "BelleSummerBodyA".startswith("BelleSummerBody") → 매칭
                name_body = sec_name[len("Resource"):] if sec_name.lower().startswith("resource") else sec_name
                mesh_name_part = name_body
                if section_buf_type:
                    mesh_name_part = name_body[:-len(section_buf_type)] if name_body.endswith(section_buf_type) else name_body
                section_mesh_key = max(
                    (k for k in mesh_strides_map if k.startswith(mesh_name_part) and mesh_name_part),
                    key=len,
                    default=None,
                )
            continue
        if not in_resource or stripped.startswith(";"):
            continue
        m = _STRIDE_INI_RE.match(line)
        if m:
            stride_line_idx = i
            stride_value = int(m.group(2))

    flush_section()

    if not changes:
        return 0

    for line_idx, new_stride, old_stride in changes:
        old_line = lines[line_idx]
        m = _STRIDE_INI_RE.match(old_line)
        if m:
            lines[line_idx] = old_line[: m.start(2)] + str(new_stride) + old_line[m.end(2):]
            op.report(
                {"INFO"},
                f"[ini stride 수정] {os.path.basename(ini_path)}: {old_stride} → {new_stride}",
            )

    try:
        with open(ini_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception as e:
        op.report({"WARNING"}, f"[ini stride] 쓰기 실패: {ini_path} ({e})")
        return 0

    return len(changes)


def fix_ini_buf_strides(op, ini_dir, asset_path):
    """
    export_vb 실행 전 사전처리:
    vb0 txt element 정의를 기반으로 ini의 Resource stride를 수정합니다.

    - asset_path: hash.json 경로 또는 에셋 폴더 경로
    """
    if os.path.isfile(asset_path):
        asset_dir = os.path.dirname(os.path.normpath(asset_path))
    else:
        asset_dir = os.path.normpath(asset_path)

    mesh_strides_map = _collect_vb0_strides(asset_dir)
    if not mesh_strides_map:
        op.report({"WARNING"}, "[ini stride] asset 폴더에서 vb0 stride 정보를 읽지 못했습니다")
        return 0

    total_fixed = 0
    for root, _, files in os.walk(ini_dir):
        for fname in files:
            if fname.lower().endswith(".ini"):
                total_fixed += _fix_ini_strides_by_vb0(
                    op, os.path.join(root, fname), mesh_strides_map
                )
    return total_fixed


# ---------------------------------------------------------------------------
# buf 재패킹: ini stride보다 실제 buf가 짧으면 0 패딩으로 보정
# ---------------------------------------------------------------------------

def _parse_buf_groups_from_ini(ini_path):
    """
    ini 파일의 Resource 섹션을 파싱해 버퍼 그룹을 반환합니다.
    반환: {mesh_name: {"Position": (stride, abs_path), "Blend": ..., "Texcoord": ...}}
    """
    ini_dir = os.path.dirname(ini_path)
    groups = {}
    in_resource = False
    cur_buf_type = None
    cur_mesh = None
    cur_stride = None
    cur_filename = None

    def flush():
        nonlocal cur_buf_type, cur_mesh, cur_stride, cur_filename
        if cur_mesh and cur_buf_type and cur_stride and cur_filename:
            groups.setdefault(cur_mesh, {})[cur_buf_type] = (
                cur_stride,
                os.path.join(ini_dir, cur_filename),
            )
        cur_buf_type = cur_mesh = cur_stride = cur_filename = None

    try:
        with open(ini_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return groups

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            flush()
            end = stripped.find("]")
            sec_name = stripped[1:end] if end > 0 else stripped[1:]
            in_resource = sec_name.lower().startswith("resource")
            cur_buf_type = cur_mesh = cur_stride = cur_filename = None
            if in_resource:
                name_body = sec_name[8:]  # "Resource" 제거 (8글자)
                for bt in ("Texcoord", "Blend", "Position"):
                    if name_body.endswith(bt):
                        cur_buf_type = bt
                        cur_mesh = name_body[:-len(bt)]
                        break
            continue
        if not in_resource or not cur_buf_type or stripped.startswith(";"):
            continue
        m = _STRIDE_INI_RE.match(line)
        if m:
            cur_stride = int(m.group(2))
            continue
        m = _FILENAME_INI_RE.match(line)
        if m:
            val = m.group(1).strip()
            val = re.split(r";|#", val)[0].strip().strip('"').strip("'")
            cur_filename = os.path.basename(val)

    flush()
    return groups


def repack_short_buf_files(op, ini_dir):
    """
    export_vb 실행 전 사전처리:
    ini의 Resource stride보다 실제 .buf 파일이 짧은 경우 (stride가 잘못 작아진 경우)
    각 vertex 끝에 0 패딩을 추가해 올바른 크기로 재패킹합니다.

    Position buf 크기 / Position stride = vertex_count 를 기준으로 판단합니다.
    """
    total_repacked = 0

    for root, _, files in os.walk(ini_dir):
        for fname in files:
            if not fname.lower().endswith(".ini"):
                continue
            groups = _parse_buf_groups_from_ini(os.path.join(root, fname))

            for mesh_name, bufs in groups.items():
                if "Position" not in bufs:
                    continue
                pos_stride, pos_path = bufs["Position"]
                if not os.path.isfile(pos_path) or pos_stride <= 0:
                    continue
                pos_size = os.path.getsize(pos_path)
                if pos_size % pos_stride != 0:
                    continue
                vertex_count = pos_size // pos_stride

                for buf_type, (expected_stride, buf_path) in bufs.items():
                    if buf_type == "Position":
                        continue
                    if not os.path.isfile(buf_path):
                        continue
                    buf_size = os.path.getsize(buf_path)
                    if vertex_count == 0 or buf_size % vertex_count != 0:
                        continue
                    actual_stride = buf_size // vertex_count
                    if actual_stride >= expected_stride:
                        continue  # 이상 없음

                    pad_size = expected_stride - actual_stride
                    padding = b"\x00" * pad_size
                    try:
                        with open(buf_path, "rb") as f:
                            data = f.read()
                        new_data = bytearray()
                        for i in range(vertex_count):
                            new_data += data[i * actual_stride: i * actual_stride + actual_stride]
                            new_data += padding
                        with open(buf_path, "wb") as f:
                            f.write(new_data)
                        total_repacked += 1
                        op.report(
                            {"INFO"},
                            f"[buf 재패킹] {os.path.basename(buf_path)}: {actual_stride} → {expected_stride} bytes/vertex",
                        )
                    except Exception as e:
                        op.report(
                            {"WARNING"},
                            f"[buf 재패킹 실패] {os.path.basename(buf_path)}: {e}",
                        )

    return total_repacked
