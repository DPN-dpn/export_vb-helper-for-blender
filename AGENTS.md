# AGENTS.md — export_vb-helper-for-blender

이 파일은 AI 에이전트(Copilot, Antigravity 등)가 이 프로젝트를 올바르게 이해하고 기여할 수 있도록 작성된 컨텍스트 문서입니다.

---

## 프로젝트 개요

**엵툵 도우미**는 XXMI 계열 게임 모딩 도구인 `export_vb.py`(일명 엵툵)의 사용을 보조하기 위한 **Blender 애드온**입니다.

- **목적:** 모드 `.ini` 파일의 Resource 섹션과 에셋 `hash.json` 파일의 컴포넌트 슬롯을 시각적인 노드 기반 UI로 매칭하고, 최종적으로 `export_vb.py`까지 연동하여 내보내기까지 처리합니다.
- **버전:** 1.4.1
- **지원 Blender:** 3.6.23 이상
- **라이센스:** MIT
- **저장소:** https://github.com/DPN-dpn/export_vb-helper-for-blender

---

## 아키텍처 개요

```
__init__.py                   # 애드온 진입점, bl_info 정의, 모듈 등록/해제
source/
├── addon/                    # 애드온 환경설정 패널 (우측 N-패널)
│   ├── __init__.py
│   └── panel.py              # 우측 패널 UI (export_vb 경로, 업데이트 체크)
├── core/                     # 핵심 Blender 데이터 바인딩
│   ├── __init__.py
│   ├── preferences.py        # AddonPreferences (EVBHPreferences), 씬 프로퍼티 등록
│   └── properties.py         # bpy.types.Scene 프로퍼티 등록/해제, 텍스처 소켓 토글 로직
├── data/
│   └── text_data_block.py    # bpy.data.texts 관리 (ASSET/MOD 텍스트 블록 생성·삭제)
├── node_tree_editor/         # 핵심: 노드 에디터 관련 모든 코드
│   ├── __init__.py
│   ├── editor.py             # NodeEditor 커스텀 헤더 UI (툴바 버튼 배치)
│   ├── nodes.py              # 커스텀 노드 클래스 정의
│   ├── sockets.py            # 커스텀 소켓 클래스 정의
│   ├── tree.py               # EVBH_NodeTree (커스텀 NodeTree 타입) 정의
│   └── operators/
│       ├── __init__.py
│       ├── importer.py       # 파일 불러오기 오퍼레이터 (모드 폴더, hash.json)
│       ├── creater.py        # 노드 트리 생성 오퍼레이터 (슬롯 매칭 시작하기)
│       ├── linker.py         # 자동 연결 / 모든 연결 해제 오퍼레이터
│       ├── exporter.py       # 내보내기 오퍼레이터 (EVBH_OT_export_mod)
│       └── functions/        # 내보내기 파이프라인 헬퍼 모듈들
│           ├── collector.py      # 노드 트리에서 매핑 정보 수집
│           ├── ini_parser.py     # .ini 파일 파싱/직렬화
│           ├── preprocessor.py   # ini 전처리 (섹션 정리)
│           ├── replacer.py       # ini 내 문자열 교체 (파일명 변경)
│           ├── run_export_vb.py  # export_vb.py 외부 프로세스 실행
│           └── fmt_fixer.py      # ini stride 보정 및 .buf 파일 재패킹
├── text_editor/              # 선택된 에셋/모드 파일 내용 텍스트 뷰어
│   ├── __init__.py
│   └── editor.py             # TEXT_EDITOR 영역 커스텀 헤더 UI
├── updator/                  # 자동 업데이트
│   ├── __init__.py
│   ├── operators.py          # 업데이트 체크/실행, GitHub/Wiki 열기 오퍼레이터
│   └── panel.py              # 업데이트 관련 패널 UI
└── workspace/                # 전용 워크스페이스 관리
    ├── __init__.py
    └── workspace.py          # 'EVBH.blend'로부터 작업 영역 자동 추가
```

---

## 핵심 개념 및 데이터 흐름

### 1. 데이터 블록 (text_data_block)
- 불러온 `hash.json`과 `.ini` 파일들은 `bpy.data.texts`에 텍스트 블록으로 저장됩니다.
- 각 블록은 `"ASSET"` 또는 `"MOD"` 태그로 분류됩니다.
- `_asset_text_blocks`와 `_mod_text_blocks` 집합(set)에 이름이 관리됩니다.

### 2. 노드 타입
| 클래스 | `bl_idname` | 역할 |
|---|---|---|
| `EVBH_ModFileNode` | `EVBH_ModFileNode` | .ini 파일 하나를 대표. 출력 소켓에 Resource 파일들이 연결됨 |
| `EVBH_AssetSlotNode` | `EVBH_AssetSlotNode` | hash.json의 컴포넌트 하나를 대표. 입력 소켓에 모드 소켓이 연결됨 |
| `EVBH_ResultNode` | `EVBH_ResultNode` | 연결 결과를 집약. 내보내기 버튼 포함 |

### 3. 소켓 타입 (색상으로 구분)
| 클래스 | 색상 | 용도 |
|---|---|---|
| `EVBH_PositionSocket` | 주황 | vb0 (Position 버퍼) |
| `EVBH_BlendSocket` | 보라 | vb2 (Blend 버퍼) |
| `EVBH_TexcoordSocket` | 초록 | vb1 (Texcoord 버퍼) |
| `EVBH_IBSocket` | 파랑 | IB (Index 버퍼) |
| `EVBH_TextureSocket` | 회녹 | 텍스처 파일 (.dds 등) |
| `EVBH_ResultSocket` | 검정 | 에셋→Result 노드 연결용 |

- 모든 소켓은 커스텀 속성 `["hash"]`에 해시값을 저장합니다.
- `EVBH_IBSocket`과 `EVBH_TextureSocket`은 추가로 `["classification"]` 속성을 가질 수 있습니다.
- `EVBH_TextureSocket` (ModFileNode 출력)은 `["all_hashes"]` 속성(쉼표 구분)을 가질 수 있습니다.

### 4. 씬 프로퍼티 (`bpy.types.Scene`)
| 프로퍼티 | 타입 | 설명 |
|---|---|---|
| `evbh_asset_path` | StringProperty | 선택된 hash.json 경로 |
| `evbh_mod_path` | StringProperty | 선택된 모드 폴더 경로 |
| `evbh_current_asset_path` | StringProperty | 현재 노드 트리에 적용된 에셋 경로 |
| `evbh_current_mod_path` | StringProperty | 현재 노드 트리에 적용된 모드 폴더 경로 |
| `evbh_export_path` | StringProperty | 내보내기 대상 폴더 |
| `evbh_show_texture_sockets` | BoolProperty | 텍스처 소켓 표시 여부 (토글 시 소켓 동적 생성/제거) |

### 5. AddonPreferences (`EVBHPreferences`)
| 프로퍼티 | 설명 |
|---|---|
| `evbh_export_vb` | `export_vb.py` 파일 경로 |
| `evbh_export_vb_use` | 내보내기 시 export_vb.py 연동 여부 |

---

## 오퍼레이터 목록

| `bl_idname` | 클래스 | 기능 |
|---|---|---|
| `evbh.select_asset` | `EVBH_OT_select_asset` | hash.json 파일 선택 |
| `evbh.select_mod` | `EVBH_OT_select_mod` | 모드 폴더 선택 (하위 .ini 전체 로드) |
| `evbh.unlink_asset` | `EVBH_OT_unlink_asset` | 에셋 텍스트 블록 삭제 |
| `evbh.unlink_mod` | `EVBH_OT_unlink_mod` | 모드 텍스트 블록 삭제 |
| `evbh.create_new_tree` | `EVBH_OT_create_new_tree` | 노드 트리 생성 (슬롯 매칭 시작) |
| `evbh.auto_link` | `EVBH_OT_auto_link` | 해시값 기반 자동 연결 |
| `evbh.unlink` | `EVBH_OT_unlink` | 모든 링크 해제 |
| `evbh.export_mod` | `EVBH_OT_export_mod` | 모드 내보내기 (ini 생성, 파일 복사, export_vb 실행) |
| `evbh.check_update` | `EVBH_OT_CheckUpdate` | GitHub API로 업데이트 확인 |
| `evbh.do_update` | `EVBH_OT_DoUpdate` | 최신 릴리스 zip 다운로드 후 애드온 갱신 |
| `evbh.open_github` | `EVBH_OT_OpenGithub` | GitHub 페이지 열기 |
| `evbh.open_wiki` | `EVBH_OT_OpenWiki` | Wiki 페이지 열기 |
| `evbh.install_workspace` | *(workspace 모듈)* | EVBH.blend에서 작업 영역 설치 |

---

## 내보내기 파이프라인 (exporter.py + functions/)

`evbh.export_mod` 실행 시 다음 순서로 처리됩니다:

```
1. collector.collect_result_mappings()   → 노드 트리에서 매핑 정보 수집
2. collector.collect_need_sockets()      → 내보낼 소켓(파일) 목록 추출
3. create_ini_contents()                → 필요한 ini 섹션만 추출
4. collector.collect_matching_strings()  → 파일명 변환 규칙 수집
5. preprocessor.preprocess_ini()        → ini 전처리 (Constants, Present 등 특수 섹션 처리)
6. replacer.replace_strings()           → ini 내 파일명 문자열 교체
7. create_exported_files()              → 출력 폴더 생성, 파일 복사, ini 파일 작성
8. (옵션) fmt_fixer.fix_ini_buf_strides()    → vb0 element 기준으로 ini stride 보정
9. (옵션) fmt_fixer.repack_short_buf_files() → .buf 파일 0-패딩 재패킹
10. (옵션) run_export_vb.run_export_vb()     → export_vb.py 외부 프로세스 실행
```

---

## 코딩 컨벤션

- **네이밍 접두사:** 모든 커스텀 Blender 타입/오퍼레이터/소켓은 `EVBH_` 접두사를 사용합니다.
- **씬 프로퍼티:** `bpy.types.Scene`에 등록하는 모든 커스텀 프로퍼티는 `evbh_` 접두사를 사용합니다.
- **씬 임시 데이터:** `context.scene["evbh.xxx"]` 형태의 딕셔너리 키로 런타임 상태를 저장합니다 (예: `evbh.latest_version`, `evbh.update_available`).
- **오류 처리:** 대부분의 Blender API 호출은 `try/except Exception` 블록으로 보호합니다.
- **모듈 등록 패턴:** 각 서브모듈은 `classes = (...)` 튜플과 `register()` / `unregister()` 함수를 가지며, 최상위 `__init__.py`에서 순서를 맞추어 호출합니다 (unregister는 역순).
- **언어:** UI 레이블, `report()` 메시지, 주석은 한국어로 작성합니다.
- **ini 파싱:** `.ini` 파일을 파싱할 때는 `functions/ini_parser.py`의 `parse_ini()` 또는 `parse_defunctionalized_ini()`를 사용합니다. 직접 정규식으로 파싱하지 마세요.

---

## 주의사항

- `EVBH_AssetSlotNode`의 Result 출력 소켓은 단일 링크만 허용합니다 (`update()` 메서드에서 초과 링크 자동 제거).
- `EVBH_ResultNode`의 입력 소켓은 동적으로 추가/제거됩니다. 항상 마지막 소켓은 비워둡니다.
- 텍스처 소켓 토글(`evbh_show_texture_sockets`)은 소켓을 실제로 삭제/재생성합니다. 비표시 상태일 때의 소켓 데이터는 노드의 `["_evbh_saved_texture_sockets"]` 커스텀 속성에 저장됩니다.
- 업데이트 후에는 반드시 Blender를 재시작해야 합니다.
- GitHub API URL: `https://api.github.com/repos/DPN-dpn/export_vb-helper-for-blender/releases/latest`
