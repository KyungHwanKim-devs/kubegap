# 사람 없이 돌리기와 예약 실행

English: [HEADLESS.md](../HEADLESS.md)

`/kubegap`은 사람이 직접 답하는 대화형 세션을 기준으로 만들었습니다. 리포트 언어를 묻고, kube 컨텍스트를 확인하고, 처음 실행이라면 클러스터나 내 컴퓨터에 빠진 것을 물은 뒤 리포트까지 씁니다. 언어와 컨텍스트만 정해지면 그다음부터는 사람이 키보드 앞에 있지 않아도 됩니다.

이 문서에서는 터미널을 열어 두지 않고 `claude -p`나 `codex exec`로 같은 스킬을 돌리는 방법과, 이것을 매일 돌도록 예약하는 방법을 설명합니다.

사람이 있을 때와 똑같은 점이 두 가지 있습니다. kubegap은 클러스터를 읽기만 하고 Secret 값을 읽지 않습니다. 그리고 에이전트가 스냅샷에서 읽은 내용은 그 에이전트의 모델 API로 갑니다. 스냅샷은 점검 한 번에 모은 데이터를 담는 폴더이고, 자세한 내용은 [DATA.md](DATA.md)에 있습니다.

예약은 직접 만드세요. 에이전트 세션은 crontab 항목, systemd 타이머, CronJob, CI 작업을 스스로 만들거나 고치지 않습니다. `SKILL.md` 9절의 규칙입니다. 이 문서의 예시에서 시작하면 됩니다.

## 1. 질문에 미리 답해 두기

리포트 언어와 클러스터, 이 두 질문은 답이 없으면 실행이 멈춥니다. 빠진 것을 묻는 첫 실행 질문은 선택입니다. 사람 없이 돌릴 때는 답이 없는 질문을 그대로 두고 그 부분을 뺀 채 끝까지 돌아가므로, 필요한 것은 여기서 정해 두세요. `~/.kubegap/config.yaml`에 아래 키를 넣으세요.

```yaml
language: en              # 또는 ko. 없으면 스킬이 묻습니다
context: prod             # 점검할 kube 컨텍스트
confirm_context: false    # "이 컨텍스트를 점검할까요?"를 묻지 않습니다. 명령줄에 --context를 줘도 묻지 않습니다
install_tools: never      # 또는 always. 기본값 ask는 사람 없이 돌릴 때 없는 도구를 빼고 돌립니다
node_access: ssh          # k3s 같은 SSH 플랫폼: 노드를 SSH로 읽습니다. 정해 두지 않으면 어떤 노드에도 접속하지 않습니다. none = 절대 접속하지 않습니다
ssm_document: never       # EKS 전용. never = SSM 문서가 없으면 노드 OS 점검을 건너뜁니다. always = 묻지 않고 올립니다
```

설정 파일에 `context`가 있어도 명령줄에 `--context <name>`을 함께 주세요. 예약 작업이 엉뚱한 클러스터를 점검하는 일이 바로 컨텍스트 질문이 막으려는 실수입니다. 그리고 crontab을 읽는 사람이 어느 클러스터를 건드리는 작업인지 알 수 있는 곳도 이 옵션뿐입니다.

사람 없이 돌리는데 언어나 클러스터가 정해지지 않았으면, 스킬은 어떤 키를 넣으면 되는지 알려 주고 멈춥니다. 로그에는 멈춘 실행으로 남기 때문에 추측으로 쓴 리포트가 조용히 나오는 일은 없습니다.

첫 실행 질문의 답이 비어 있으면 실행은 멈추지 않습니다. 그 질문 때문에 설치하거나 올리거나 접속하는 것은 없고, 무엇이 빠졌는지 리포트에 적습니다. `scripts/kubegap config set <key> <value>`를 쓰면 파일을 열지 않고 위 키를 쓸 수 있습니다. `context`만 파일에 직접 적으세요.

## 2. 사람 없이 돌리는 명령

**Claude Code.** `-p`는 결과를 출력하고 끝납니다. 스킬에 셸과 파일 도구가 필요하니 이번 실행에서 허용하세요. 이 방법은 `--dangerously-skip-permissions`보다 허용 범위가 좁고, `--dangerously-skip-permissions`는 필요 없습니다.

```bash
claude -p "/kubegap daily --context prod" --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebFetch"
```

**Codex.** `codex exec`는 프롬프트 하나를 실행하고 끝납니다. 기본 샌드박스는 네트워크가 없고 작업 폴더 안에만 쓸 수 있습니다. 그런데 점검은 API 서버와 통신하고, Prometheus와 Loki를 포트포워드하고, EKS에서는 AWS CLI를 호출하고, `~/.kubegap/` 아래에 스냅샷을 씁니다. 그래서 이 프로세스에서는 샌드박스를 열어야 합니다. 샌드박스 설정은 에이전트가 내 컴퓨터에서 무엇을 건드릴 수 있는지를 정할 뿐이고, 클러스터를 읽기만 한다는 규칙은 그대로 적용됩니다.

```bash
codex exec --sandbox danger-full-access --skip-git-repo-check -C ~ \
  -o ~/.kubegap/last-run.md '$kubegap daily --context prod'
```

작은따옴표는 셸이 `$kubegap`을 변수로 풀지 못하게 막습니다. Codex 프롬프트에서는 스킬을 `$kubegap`처럼 부릅니다. `-o`는 에이전트의 마지막 메시지를 파일로 저장합니다. 마지막 메시지는 스킬이 리포트를 저장한 뒤 출력하는 브리핑이고, 이 파일을 읽거나 다른 사람에게 전달할 수 있습니다.

리포트 글은 이 실행이 같은 CLI로 띄우는 에이전트들이 씁니다. 조치 검증, 글쓴이, 사실 대조, 문장 교체가 단계마다 `claude -p`나 `codex exec` 하나씩 돕니다. 같은 로그인을 쓰고, 셸은 없고, 답변 말고는 아무것도 쓰지 않습니다. `workspace-write`처럼 이걸 허용하지 않는 Codex 샌드박스에서는 스킬이 그 단계를 직접 하고 브리핑에 그렇게 적습니다.

예약하기 전에 명령을 손으로 한 번 실행하세요. `install_tools: always`라면 첫 실행에서 추가 도구를 설치하고, EKS에서는 SSM 문서가 필요할 수 있습니다. 둘 다 cron 로그로 디버깅하는 것보다 직접 지켜보는 편이 쉽습니다.

## 3. cron 예시

```cron
# crontab -e
# cron은 셸 프로필을 읽지 않습니다. claude, kubectl, aws, jq가 있는 폴더와 kubeconfig를 지정하세요
PATH=/opt/homebrew/bin:/usr/local/bin:/home/me/.local/bin:/usr/bin:/bin
KUBECONFIG=/home/me/.kube/config

# 평일 08:30에 daily 점검, 한 번에 하나만 실행합니다
30 8 * * 1-5  flock -n /tmp/kubegap-prod.lock claude -p "/kubegap daily --context prod" --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebFetch" >> /home/me/.kubegap/cron.log 2>&1

# 일요일 밤에 full 점검
0 22 * * 0    flock -n /tmp/kubegap-prod.lock claude -p "/kubegap full --context prod" --allowedTools "Bash,Read,Write,Edit,Glob,Grep,WebFetch" >> /home/me/.kubegap/cron.log 2>&1

# 최근 daily 스냅샷 14개와 full 스냅샷 4개만 남깁니다. full 스냅샷 하나는 40 MB쯤 됩니다
0 23 * * 0    /home/me/src/kubegap/scripts/kubegap prune --context prod --keep-daily 14 --keep-full 4 >> /home/me/.kubegap/cron.log 2>&1
```

Codex를 쓴다면 `claude -p …` 부분을 위의 `codex exec …` 줄로 바꾸세요. 경로는 절대 경로로 쓰세요. cron 구현 대부분은 환경 변수 줄의 `$HOME`이나 `~`를 풀어 주지 않습니다.

`flock -n`은 이전 실행이 아직 돌고 있으면 이번 실행을 건너뜁니다. macOS에는 `flock`이 기본으로 없으니 이 부분을 빼거나 `brew install flock`으로 설치하세요.

자격 증명은 브라우저 없이 동작해야 합니다. 그 컴퓨터에서 `claude`와 `codex`가 이미 로그인되어 있거나, 환경 변수로 API 키를 받아야 합니다. EKS에서 SSO처럼 자격 증명이 만료되는 AWS 프로파일을 쓰면, 세션이 끝난 다음 날 아침 첫 실행이 실패합니다. 예약 작업에는 장기 자격 증명이나 인스턴스 자격 증명을 쓰는 프로파일을 지정하세요.

## 4. 리포트가 저장되는 곳

점검할 때마다 `~/.kubegap/snapshots/<context>/<YYYY-MM-DDTHH-MM-SS>/` 폴더가 하나 생깁니다. 이 폴더에 `report.md`, `report-details.md`, 모은 데이터가 들어 있습니다. 컨텍스트 `prod`의 가장 최근 리포트는 이렇게 볼 수 있습니다.

```bash
cat "$(ls -dt ~/.kubegap/snapshots/prod/*/ | head -1)report.md"
```

daily 리포트는 지난 daily 스냅샷과 비교합니다. 그래서 daily 점검을 예약해 두면 다른 설정 없이도 매일 아침 어제와 달라진 내용을 볼 수 있습니다. 폴더가 끝없이 커지지 않게 하려면 `scripts/kubegap prune`을 돌리거나 [`config.example.yaml`](../../config.example.yaml)의 `retention` 키를 쓰세요.
