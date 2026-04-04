## 해당 코드는 생성형AI의 도움을 통해 만들어 졌음을 알려드립니다.


# 미리보기
![previewonline-video-cutter com-ezgif com-video-to-gif-converter](https://github.com/user-attachments/assets/c7666d55-9be6-47ae-a909-04da6edd647f)


# 기능
xxmi 모드파일 추출용 프로그램인 export_vb.py를 사용하기 편하도록 하는 **파일 매칭 및 ini 내용 정리 블렌더용 애드온**


# 적용법
<img width="662" height="552" alt="install" src="https://github.com/user-attachments/assets/5ba7fdf4-b245-4baf-add6-cd61cb22aede" />

다운받은 파이썬 코드를 블렌더에서 애드온 설치 후 활성화

<img width="424" height="79" alt="install 2" src="https://github.com/user-attachments/assets/7d3a33b2-d9c6-46d0-9872-c0172cbcad5f" />

활성화 후 잠시 후 작업 영역이 자동 추가됩니다.


# 사용법
### 1. 상단 작업 영역에서 '엵툵 도우미' 작업영역으로 이동
<img width="424" height="79" alt="install 2" src="https://github.com/user-attachments/assets/7d3a33b2-d9c6-46d0-9872-c0172cbcad5f" />

#### 1-1. 툴바 설명
<img width="472" height="20" alt="1-1" src="https://github.com/user-attachments/assets/6c848e04-ff1f-4308-8143-ab914f015079" />

- <img width="32" height="20" alt="i1" src="https://github.com/user-attachments/assets/75357313-4737-4af2-98c7-e327969cb39f" />
  : 뷰 선택. 건들 필요 없음.
- <img width="115" height="20" alt="i2" src="https://github.com/user-attachments/assets/dfd3d75b-0e52-449c-8e59-52d510169e2a" />
  : 모드 폴더 선택
- <img width="115" height="20" alt="i3" src="https://github.com/user-attachments/assets/1099c670-13d3-438a-8f9a-e1a5605a1354" />
  : 에셋 json파일 선택
- <img width="20" height="20" alt="i4" src="https://github.com/user-attachments/assets/962458ff-1d39-461c-96ff-49a3e5817e39" />
  : 슬롯 매칭 시작하기
- <img width="21" height="20" alt="i5" src="https://github.com/user-attachments/assets/4249fba6-11ed-4ea5-9f56-756d0011672f" />
  : 자동 연결
- <img width="21" height="20" alt="i6" src="https://github.com/user-attachments/assets/f61ae653-b4f8-45cf-968c-efc10986e040" />
  : 모든 연결 해제
- <img width="21" height="20" alt="i7" src="https://github.com/user-attachments/assets/425ea547-2ce3-49f5-97a7-1eceba7cf4b5" />
  : 내보내기
- <img width="20" height="20" alt="i8" src="https://github.com/user-attachments/assets/d1dc8276-3bc9-429f-b049-cb65f71ba82e" />
  : 텍스처 소켓 활성화. 현재 도움되는 기능은 없음.

#### 1-2. 패널 설명
<img width="185" height="174" alt="image" src="https://github.com/user-attachments/assets/c14594f0-d037-410b-8db7-ee6f38bcc0d3" /><br>
우측 패널에서 export_vb.py를 연결할 수 있습니다.<br>
업데이트 체크로 간편 업데이트할 수 있습니다. 업데이트 후 블렌더를 재시작해주어야 합니다.<br>

#### 1-3. 좌측 텍스트 설명
<img width="438" height="135" alt="1-3" src="https://github.com/user-attachments/assets/ffceb3e0-8003-48a0-9422-da8760ab98ff" /><br>
좌측 뷰에서 선택된 에셋의 json파일이나 모드의 ini파일을 열람할 수 있습니다.<br>

### 2. 모드 폴더, 에셋 파일 선택 후 '슬롯 매칭 시작하기' 클릭
<img width="660" height="538" alt="2" src="https://github.com/user-attachments/assets/f2632737-9854-4e79-a90d-455e2bd5b3cf" />

### 3. '자동 연결' 클릭
<img width="660" height="495" alt="3" src="https://github.com/user-attachments/assets/fbfe15df-72ed-4514-97db-50d38220ac8b" /><br>
단순 해시값을 매칭하여 연결합니다.

### 4. 남은 소켓 수동 연결
![4](https://github.com/user-attachments/assets/83300188-1bf1-47ff-95c5-381ed3d1ef59)<br>
'자동 연결'기능으로 매칭되지 않은 소켓이나, 잘못 연결된 소켓을 직접 연결합니다.

### 5. 내보내기
<img width="310" height="131" alt="5" src="https://github.com/user-attachments/assets/ce89c32e-d891-41ad-b5f7-dac70550ae2e" /><br>
툴바의 '내보내기'와 Result 노드의 '내보내기'는 동일한 동작을 합니다.

### 5-1. 엵툵으로 내보내기
<img width="184" height="86" alt="5-1" src="https://github.com/user-attachments/assets/1247a7a2-d97e-4d3f-8fe0-6acd1020088e" /><br>
우측 패널 또는 애드온 환경설정에서 엵툵을 설정할 경우, '엵툵으로 내보내기'를 설정할 수 있습니다.<br>
'엵툵으로 내보내기'를 활성화한 채로 '내보내기'를 실행할 경우, export_vb.py까지 실행 후 내보내집니다.


# 라이센스
This project is licensed under the [MIT License](LICENSE).

© 2026 DPN-dpn
