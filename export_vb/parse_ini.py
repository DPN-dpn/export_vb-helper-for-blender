import os
import pprint

class ini_parser(object):
    totalstr = {}
    vb = {}

    def __init__(self, inifile):
        print("[INIT] 시작 - ini 파일 파싱 시도:", inifile)
        try:
            self.ini_file = self.parse_ini(inifile)
            print("[INIT] 파싱 완료")
        except Exception as e:
            print(f"[ERROR][INIT] 파싱 실패: {e}")
            raise

    def parse_section(self, section):
        print("[PARSE_SECTION] 시작")
        mod_data = {}
        recognized_header = ("[TextureOverride", "[ShaderOverride", "[Resource", "[Constants", "[Present", "[CommandList", "[CustomShader")
        try:
            for line in section.splitlines():
                if not line.strip() or line[0] == ";":  # comments and empty lines
                    continue

                # Headers
                for header in recognized_header:
                    if header in line:
                        if "CommandListReflectionTexture" in line or "CommandListOutline" in line:
                            print("[PARSE_SECTION] 특정 CommandList 필터링, 빈 dict 반환")
                            return {}
                        mod_data["header"] = header[1:]
                        mod_data["name"] = line.split(header)[1][:-1]
                        break

                # Conditionals
                if "==" in line:
                    key, data = line.split("==", 1)
                    mod_data[key.strip()] = data.strip()
                elif "endif" in line:
                    mod_data["endif"] = ""
                # Properties
                elif "=" in line:
                    key, data = line.split("=")
                    if "CharacterIB" in key or "ResourceRef" in key:
                        continue
                    mod_data[key.strip()] = data.strip()
            print("[PARSE_SECTION] 완료:", mod_data.get("name", "Unnamed"))
            return mod_data
        except Exception as e:
            print(f"[ERROR][PARSE_SECTION] 실패: {e}")
            raise

    def parse_ini(self, ini_file):
        print("[PARSE_INI] 시작 - 파일 열기:", ini_file)
        ini_group = 0
        all_mod_data = []
        try:
            with open(ini_file, "r", encoding="utf-8") as f:
                ini_text = ["[" + x.strip() for x in f.read().split("[")]
            print(f"[PARSE_INI] 섹션 개수: {len(ini_text) - 1}")
            for section in ini_text[1:]:
                mod_data = self.parse_section(section)
                mod_data["location"] = os.path.dirname(ini_file)
                mod_data["ini_group"] = ini_group
                all_mod_data.append(mod_data)
            print("[PARSE_INI] 완료 - 총 섹션 수:", len(all_mod_data))
            return all_mod_data
        except Exception as e:
            print(f"[ERROR][PARSE_INI] 실패: {e}")
            raise

    def collect_self_fmt(self):
        print("[COLLECT_SELF_FMT] 시작")
        try:
            stride_data = self.collect_stride(self.ini_file)
            ib_data = self.collect_ib_data(self.ini_file)
            print("[COLLECT_SELF_FMT] 완료")
            return stride_data, ib_data
        except Exception as e:
            print(f"[ERROR][COLLECT_SELF_FMT] 실패: {e}")
            raise

    def collect_stride(self, all_mod_data):
        print("[COLLECT_STRIDE] 시작")
        vbfiles = {}
        try:
            for i in range(len(all_mod_data)):
                if "stride" in all_mod_data[i]:
                    if "Position" in all_mod_data[i]['name']:
                        vbname = all_mod_data[i]['name'].replace("Position", "")
                        vbfiles[vbname] = {}
                        vbfiles[vbname]['Position'] = all_mod_data[i]
                        print(f"[COLLECT_STRIDE] Position 추가: {vbname}")
                    elif "Blend" in all_mod_data[i]['name']:
                        vbname = all_mod_data[i]['name'].replace("Blend", "")
                        vbfiles[vbname]['Blend'] = all_mod_data[i]
                        print(f"[COLLECT_STRIDE] Blend 추가: {vbname}")
                    elif "Texcoord" in all_mod_data[i]['name']:
                        vbname = all_mod_data[i]['name'].replace("Texcoord", "")
                        vbfiles[vbname]['Texcoord'] = all_mod_data[i]
                        print(f"[COLLECT_STRIDE] Texcoord 추가: {vbname}")
                    else:
                        vbfiles[all_mod_data[i]['name']] = all_mod_data[i]
                        print(f"[COLLECT_STRIDE] 단일 vbfile 추가: {all_mod_data[i]['name']}")

            if vbfiles.get("Weapon"):
                print("[COLLECT_STRIDE] Weapon 키 발견 - 처리 시작")
                vb = bytearray()
                # 처리 로직
                print("[COLLECT_STRIDE] Weapon 처리 완료")
                return self.vb
            else:
                for ibs in vbfiles:
                    vb = bytearray()
                    if "stride" in vbfiles[ibs]:
                        bufWea = os.path.join(vbfiles[ibs]['location'], vbfiles[ibs]['filename'])
                        self.totalstr[ibs] = vbfiles[ibs]["stride"]
                        print(f"[COLLECT_STRIDE] 파일 읽기 시도: {bufWea}")
                        with open(bufWea, 'rb') as buf:
                            vb = bytearray(buf.read())
                        self.vb[ibs] = vb
                        print(f"[COLLECT_STRIDE] 파일 읽기 완료: {bufWea}")
                    else:
                        ibfile = vbfiles[ibs]

                        bufPosi = os.path.join(ibfile["Position"]['location'], ibfile["Position"]['filename'])
                        bufblend = os.path.join(ibfile["Blend"]['location'], ibfile["Blend"]['filename'])
                        bufTexc = os.path.join(ibfile["Texcoord"]['location'], ibfile["Texcoord"]['filename'])
                        print(f"[COLLECT_STRIDE] Position 파일 읽기: {bufPosi}")
                        print(f"[COLLECT_STRIDE] Blend 파일 읽기: {bufblend}")
                        print(f"[COLLECT_STRIDE] Texcoord 파일 읽기: {bufTexc}")

                        with open(bufPosi, 'rb') as pfile, open(bufblend, 'rb') as bfile, open(bufTexc, 'rb') as tfile:
                            posibin = bytearray(pfile.read())
                            blendbin = bytearray(bfile.read())
                            texcbin = bytearray(tfile.read())
                        i = 0
                        posistr, blendstr, texcstr = int(ibfile["Position"]['stride']), int(ibfile["Blend"]['stride']), int(ibfile["Texcoord"]['stride'])
                        self.totalstr[ibs] = posistr + blendstr + texcstr
                        while i < len(blendbin) / blendstr:
                            vb += posibin[i * posistr:i * posistr + posistr]
                            vb += blendbin[i * blendstr:i * blendstr + blendstr]
                            vb += texcbin[i * texcstr:i * texcstr + texcstr]
                            i += 1
                        self.vb[ibs] = vb
                        print(f"[COLLECT_STRIDE] {ibs} 합쳐서 vb 생성 완료")

            print("[COLLECT_STRIDE] 완료")
            return self.vb
        except Exception as e:
            print(f"[ERROR][COLLECT_STRIDE] 실패: {e}")
            raise

    def collect_ib_data(self, all_mod_data):
        print("[COLLECT_IB_DATA] 시작")
        ibfiles = {}
        try:
            for i in range(len(all_mod_data)):
                if "format" in all_mod_data[i]:
                    ibfiles[all_mod_data[i]['filename']] = all_mod_data[i]
                    print(f"[COLLECT_IB_DATA] IB 파일 추가: {all_mod_data[i]['filename']}")
            print("[COLLECT_IB_DATA] 완료")
            return ibfiles
        except Exception as e:
            print(f"[ERROR][COLLECT_IB_DATA] 실패: {e}")
            raise

    def searchStride(self, text):
        print(f"[SEARCH_STRIDE] 검색: {text}")
        for ids in self.totalstr:
            if ids in text:
                print(f"[SEARCH_STRIDE] 매칭 발견: {ids} -> {self.totalstr[ids]}")
                return self.totalstr[ids]
        print("[SEARCH_STRIDE] 매칭 없음, 기본값 Weapon 반환")
        return "Weapon"

    def searchVB(self, text):
        print(f"[SEARCH_VB] 검색: {text}")
        for ids in self.vb:
            if ids in text:
                print(f"[SEARCH_VB] 매칭 발견: {ids}")
                return self.vb[ids]
        print("[SEARCH_VB] 매칭 없음, 기본값 Weapon 반환")
        return "Weapon"