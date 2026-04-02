import os
import shutil
import subprocess
import sys

def run_export_vb(op, evbh_export_vb, export_dir, asset_path):
    if not evbh_export_vb:
        op.report({"WARNING"}, "export_vb 경로가 설정되지 않음")
        return

    # export_vb.py 파일 경로/디렉터리 판정
    if os.path.isfile(evbh_export_vb):
        base_dir = os.path.dirname(os.path.normpath(evbh_export_vb))
        script_path = os.path.normpath(evbh_export_vb)
    else:
        base_dir = os.path.normpath(evbh_export_vb)
        script_path = os.path.join(base_dir, "export_vb.py")

    if not os.path.isdir(base_dir):
        op.report({"WARNING"}, f"export_vb 폴더를 찾을 수 없음: {base_dir}")
        return

    if not os.path.isfile(script_path):
        op.report({"WARNING"}, f"export_vb.py를 찾지 못함: {script_path}")
        return

    if not asset_path:
        op.report({"WARNING"}, "에셋 경로가 설정되지 않았습니다")
        return

    if os.path.isdir(asset_path):
        asset_src_dir = os.path.normpath(asset_path)
    elif os.path.isfile(asset_path):
        asset_src_dir = os.path.dirname(os.path.normpath(asset_path))
    else:
        op.report({"WARNING"}, f"에셋 경로를 찾을 수 없음: {asset_path}")
        return

    if not export_dir or not os.path.exists(export_dir):
        op.report({"WARNING"}, f"내보내진 모드 폴더를 찾을 수 없음: {export_dir}")
        return

    created_paths = []
    dest_mod = None

    try:
        # 1) asset 복사
        dest_asset_root = os.path.join(base_dir, "asset")
        os.makedirs(dest_asset_root, exist_ok=True)
        dest_asset_sub = os.path.join(dest_asset_root, os.path.basename(asset_src_dir))
        if os.path.exists(dest_asset_sub):
            shutil.rmtree(dest_asset_sub)
        shutil.copytree(asset_src_dir, dest_asset_sub)
        created_paths.append(dest_asset_sub)

        # 2) mods로 내보내진 폴더 이동
        dest_mods_root = os.path.join(base_dir, "mods")
        os.makedirs(dest_mods_root, exist_ok=True)
        dest_mod = os.path.join(dest_mods_root, os.path.basename(os.path.normpath(export_dir)))
        if os.path.exists(dest_mod):
            if os.path.isdir(dest_mod):
                shutil.rmtree(dest_mod)
            else:
                os.remove(dest_mod)
        shutil.move(export_dir, dest_mod)

        # 3) export_vb.py 실행
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                cwd=base_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
            if result.returncode != 0:
                op.report({"WARNING"}, f"export_vb 실행 실패: rc={result.returncode}")
                if result.stdout:
                    op.report({"INFO"}, result.stdout)
                if result.stderr:
                    op.report({"INFO"}, result.stderr)
        except Exception as e:
            op.report({"WARNING"}, f"export_vb 실행 중 예외: {e}")

        # 4) output 폴더의 결과를 원래 내보내기 부모 폴더로 이동
        output_dir = os.path.join(base_dir, "output")
        target_parent = os.path.dirname(os.path.normpath(export_dir))
        if os.path.isdir(output_dir):
            for name in os.listdir(output_dir):
                src = os.path.join(output_dir, name)
                dst = os.path.join(target_parent, name)
                try:
                    if os.path.exists(dst):
                        if os.path.isdir(dst):
                            shutil.rmtree(dst)
                        else:
                            os.remove(dst)
                    shutil.move(src, dst)
                except Exception as e:
                    op.report({"WARNING"}, f"output 이동 실패: {src} -> {dst} ({e})")
        else:
            op.report({"WARNING"}, f"output 폴더를 찾지 못함: {output_dir}")

    finally:
        # 정리: 생성한 복사본 제거 및 이동한 mods 제거
        for p in created_paths:
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p)
                elif os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
        try:
            if dest_mod and os.path.exists(dest_mod):
                if os.path.isdir(dest_mod):
                    shutil.rmtree(dest_mod)
                else:
                    os.remove(dest_mod)
        except Exception:
            pass

    op.report({"INFO"}, "export_vb 처리 완료")
