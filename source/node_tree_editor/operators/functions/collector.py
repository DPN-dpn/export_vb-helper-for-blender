import os


def collect_result_mappings(node_tree, asset_name):
    """
    수집된 매핑 정보:
    {'asset_name': 'AriaSkin',
    'inputs': [{'asset_node': [{'asset_node_name': 'Body',
                                'asset_node_type': 'EVBH_AssetSlotNode',
                                'asset_socket_name': 'Result',
                                'mods': [{'asset_input_class': '',
                                          'asset_input_hash': 'f84d5a49',
                                          'asset_input_name': 'Position',
                                          'mod_node_name': 'AriaDevil.ini',
                                          'mod_node_type': 'EVBH_ModFileNode',
                                          'mod_socket_hash': '56eaff1c',
                                          'mod_socket_name': 'AriaDevilBodyPosition.buf',
                                          'mod_socket_type': 'EVBH_PositionSocket'},
                                         {'asset_input_class': 'A',
                                          'asset_input_hash': 'c6bb960b',
                                          'asset_input_name': 'IB',
                                          'mod_node_name': 'Body.ini',
                                          'mod_node_type': 'EVBH_ModFileNode',
                                          'mod_socket_hash': 'c6bb960b',
                                          'mod_socket_name': 'AriaDevilBodyA.ib',
                                          'mod_socket_type': 'EVBH_IBSocket'},
                                         ...
                                        ]}],
                'input_index': 0,
                'input_name': 'Data 1'},
              ...
              ]}
    """
    if node_tree is None:
        return []

    # EVBH_ResultNode 찾기
    result_node = next(
        (n for n in node_tree.nodes if getattr(n, "bl_idname", "") == "EVBH_ResultNode"),
        None,
    )
    if result_node is None:
        return []

    mappings = {
        "asset_name": asset_name,
        "inputs": [],
    }
    for idx, input_sock in enumerate(result_node.inputs):
        # 각 Result 입력마다 여러 링크(여러 Asset이 올 수 있음)를 허용
        input_links = list(getattr(input_sock, "links", []))
        if not input_links:
            continue

        entry = {
            "input_index": idx,
            "input_name": getattr(input_sock, "name", ""),
            "asset_node": [],
        }

        for link in input_links:
            asset_node = getattr(link, "from_node", None)
            asset_socket = getattr(link, "from_socket", None)
            if asset_node is None:
                continue

            asset_entry = {
                "asset_node_name": getattr(asset_node, "name", ""),
                "asset_node_type": getattr(asset_node, "bl_idname", ""),
                "asset_socket_name": (
                    getattr(asset_socket, "name", "") if asset_socket else ""
                ),
                "mods": [],
            }

            # EVBH_AssetSlotNode의 각 입력 소켓(Asset이 받는 각 슬롯)에 연결된 링크들을 검사
            for a_input in getattr(asset_node, "inputs", []):
                for link2 in list(getattr(a_input, "links", [])):
                    mod_node = getattr(link2, "from_node", None)
                    mod_socket = getattr(link2, "from_socket", None)
                    if mod_node is None:
                        continue
                    input_name = getattr(a_input, "name", "")
                    mod_info = {
                        "mod_node_name": getattr(mod_node, "name", ""),
                        "mod_node_type": getattr(mod_node, "bl_idname", ""),
                        "mod_socket_name": (
                            getattr(mod_socket, "name", "") if mod_socket else ""
                        ),
                        "mod_socket_type": (
                            getattr(
                                getattr(mod_socket, "__class__", None), "bl_idname", ""
                            )
                            if mod_socket
                            else ""
                        ),
                        "mod_socket_hash": (
                            mod_socket.get("hash", "")
                            if mod_socket and hasattr(mod_socket, "get")
                            else ""
                        ),
                        "asset_input_name": (
                            input_name
                            if not input_name.startswith("IB")
                            else input_name[:2]
                        ),
                        "asset_input_hash": (
                            a_input.get("hash", "") if hasattr(a_input, "get") else ""
                        ),
                        "asset_input_class": (
                            input_name[2:].replace("_", "")
                            if input_name.startswith("IB")
                            else ""
                        ),
                    }
                    asset_entry["mods"].append(mod_info)

            entry["asset_node"].append(asset_entry)

        mappings["inputs"].append(entry)

    return mappings


def collect_need_sockets(mappings):
    """
    {'AriaDevil.ini': {'AriaDevilBodyA.ib',
                       'AriaDevilBodyB.ib',
                       'AriaDevilBodyBlend.buf',
                       'AriaDevilBodyPosition.buf',
                       'AriaDevilBodyTexcoord.buf',
                       'AriaDevilLegsA.ib',
                       'AriaDevilLegsBlend.buf',
                       'AriaDevilLegsPosition.buf',
                       'AriaDevilLegsTexcoord.buf'},
     ...
    }
    """
    mods_needed = {}
    for entry in mappings.get("inputs", []):
        for asset in entry.get("asset_node", []):
            for mod in asset.get("mods", []):
                name = mod.get("mod_node_name", "")
                sock = mod.get("mod_socket_name", "")
                if not name:
                    continue
                mods_needed.setdefault(name, set()).add(sock)
    return mods_needed


def collect_matching_strings(mappings):
    """
    'Legs.ini': {'replacements': {'AriaDevilLegsA.ib': {'new_base': 'AriaSkinLegsA.ib',
                                                        'section': 'AriaSkinLegsAIB'},
                                  ...
                                 }
                 'sockets': {'AriaDevilBodyA.ib',
                             'AriaDevilBodyB.ib',
                             ...
                            }},
    """

    matchings = {}
    if not mappings:
        return matchings

    asset_name = mappings.get("asset_name", "") or ""

    for entry in mappings.get("inputs", []):
        for asset in entry.get("asset_node", []):
            asset_node_name = asset.get("asset_node_name", "") or ""
            for mod in asset.get("mods", []):
                mod_node = mod.get("mod_node_name", "") or ""
                orig = mod.get("mod_socket_name", "") or ""
                if not mod_node or not orig:
                    continue

                sock_type = mod.get("mod_socket_type", "") or ""
                asset_input_name = mod.get("asset_input_name", "") or ""
                asset_input_class = mod.get("asset_input_class", "") or ""

                # tail 결정 (기존 규칙을 참고하여 IB/Texture는 class 기반)
                if sock_type in ("EVBH_IBSocket", "EVBH_TextureSocket"):
                    tail = asset_input_class or asset_input_name
                else:
                    tail = asset_input_name

                orig_base = os.path.basename(orig)
                orig_ext = os.path.splitext(orig_base)[1] or ""

                # 확장자 규칙
                if sock_type == "EVBH_IBSocket":
                    ext = ".ib"
                elif sock_type in (
                    "EVBH_PositionSocket",
                    "EVBH_BlendSocket",
                    "EVBH_TexcoordSocket",
                ):
                    ext = ".buf"
                elif sock_type == "EVBH_TextureSocket":
                    ext = orig_ext or ""
                else:
                    ext = orig_ext or ""

                new_base = f"{asset_name}{asset_node_name}{tail}{ext}"

                # 섹션명 규칙
                if asset_input_name == "IB":
                    section_name = f"{asset_name}{asset_node_name}{asset_input_class}{asset_input_name}"
                else:
                    section_name = f"{asset_name}{asset_node_name}{asset_input_name}"

                m = matchings.setdefault(
                    mod_node, {"sockets": set(), "replacements": {}}
                )
                m["sockets"].add(orig)
                m["replacements"][orig] = {
                    "new_base": new_base,
                    "section": section_name,
                }

    return matchings, asset_name
