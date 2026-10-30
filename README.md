# 노션 고정 구간 간트 차트

노션 프로젝트 DB를 읽어서 정해진 기간만 보이고 가로 스크롤이 없는 간트 차트를 만든다. 만든 차트는 GitHub Pages에 올리고, 노션 페이지에 `/embed`로 붙여서 쓴다.

## 동작 방식

GitHub Actions가 3시간마다 `build.py`를 실행한다. `build.py`는 노션 API로 DB를 읽고, `template.html`에 일정을 넣어 `index.html`을 만든 뒤 Pages로 배포한다. 파일을 수정해서 올리거나 Actions 탭에서 **Run workflow**를 누르면 바로 다시 만든다.

## 파일 구성

| 파일 | 역할 |
|---|---|
| `build.py` | 노션 DB를 읽어 차트 HTML을 만든다 |
| `template.html` | 차트 디자인과 그리는 방식이 들어 있다 |
| `config.json` | DB, 기간, 칸 이름 등 설정을 모아 둔다 |
| `.github/workflows/build.yml` | 자동 실행 주기와 배포 과정을 정한다 |

## 설정 (config.json)

| 키 | 뜻 |
|---|---|
| `database_id` | 읽어 올 노션 DB의 ID다 |
| `range_start`, `range_end` | 보여 줄 기간이다. `range_end`를 `"now"`로 두면 항상 이번 달까지 보여 준다 |
| `title_property` | 프로젝트 이름 칸이다 |
| `start_property`, `end_property` | 시작일, 마감일 칸이다 |
| `fallback_range_property` | 시작일이 비어 있을 때 대신 쓰는 기간 칸이다 |
| `category_property` | 색을 나누는 분류 칸이다 |
| `hide_items_outside_range` | 기간 밖 항목을 숨길지 정한다 |
| `sort` | `start_desc`는 최근 것이 위, `start_asc`는 오래된 것이 위로 간다 |

칸 이름이 DB와 다르면 이름 칸과 날짜 칸을 자동으로 찾아서 쓴다.

## 분류별 색상

| 분류 | 색 |
|---|---|
| 프로젝트 | 회청색 |
| 경진대회 | 주황 |
| 공모전 | 파랑 |

색은 `template.html`의 `--c-proj`, `--c-comp`, `--c-contest` 값으로 바꾼다.

## 차트 표시 규칙

막대를 누르면 해당 노션 페이지가 새 탭으로 열린다. 노션 권한이 없는 사람은 페이지를 열 수 없다.

마감일이 없는 항목은 진행 중으로 보고 오늘까지 그린다.

오늘 날짜가 기간 안에 있으면 빨간 세로선으로 표시한다.

날짜가 아예 없는 항목은 차트에서 뺀다.

## 보안

노션 키는 GitHub Secret(`NOTION_TOKEN`)에만 저장한다. 코드, 차트, 실행 기록 어디에도 키 값은 남지 않는다.

노션 키는 읽기 권한만 준다. 키가 있어도 노션 내용을 고치거나 새로 만들 수 없다.

차트 페이지는 검색엔진이 수집하지 않도록 막아 둔다.

차트 주소를 아는 사람은 프로젝트 이름과 기간을 볼 수 있다. 노션 페이지 안의 내용은 볼 수 없다.
