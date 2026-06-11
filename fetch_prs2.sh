#!/bin/bash
# Re-fetch PRs that returned empty data

prs=(
"redis/redis 15260"
"redis/redis 15256"
"rust-lang/rust 157656"
"rust-lang/rust 157653"
"rust-lang/rust 157650"
"rust-lang/rust 157645"
"rust-lang/rust 157642"
"rust-lang/rust 157630"
"rust-lang/rust 157629"
"rust-lang/rust 157626"
"rust-lang/rust 157622"
"microsoft/vscode 320550"
"microsoft/vscode 320547"
"microsoft/vscode 320546"
"microsoft/vscode 320545"
"microsoft/vscode 320528"
"microsoft/vscode 320527"
"microsoft/vscode 320526"
"microsoft/vscode 320525"
"microsoft/vscode 320524"
"microsoft/vscode 320523"
"microsoft/vscode 320517"
"microsoft/vscode 320511"
"microsoft/vscode 320506"
"microsoft/vscode 320503"
"microsoft/vscode 320486"
"microsoft/vscode 320478"
"microsoft/vscode 320472"
"microsoft/vscode 320467"
"kubernetes/kubernetes 139581"
"kubernetes/kubernetes 139580"
"kubernetes/kubernetes 139579"
"kubernetes/kubernetes 139573"
"kubernetes/kubernetes 139572"
"kubernetes/kubernetes 139571"
"kubernetes/kubernetes 139570"
"kubernetes/kubernetes 139569"
"openssl/openssl 31425"
"openssl/openssl 31424"
"openssl/openssl 31423"
"openssl/openssl 31421"
"openssl/openssl 31420"
"openssl/openssl 31419"
"openssl/openssl 31418"
"openssl/openssl 31412"
"openssl/openssl 31411"
"openssl/openssl 31410"
"openssl/openssl 31409"
"openssl/openssl 31408"
"openssl/openssl 31407"
"openssl/openssl 31405"
"openssl/openssl 31401"
"apache/cassandra 4872"
"apache/cassandra 4871"
"apache/cassandra 4870"
"apache/cassandra 4869"
"apache/cassandra 4866"
"apache/cassandra 4861"
"apache/cassandra 4860"
"apache/cassandra 4859"
"apache/cassandra 4858"
"apache/cassandra 4857"
"apache/cassandra 4855"
)

for entry in "${prs[@]}"; do
  repo=$(echo "$entry" | awk '{print $1}')
  pr=$(echo "$entry" | awk '{print $2}')
  result=$(curl -s "https://api.github.com/repos/${repo}/pulls/${pr}" 2>/dev/null)
  additions=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('additions','ERR'))" 2>/dev/null)
  if [ "$additions" = "ERR" ] || [ -z "$additions" ]; then
    echo "${repo},${pr},FETCH_FAILED,0,0,0,0"
  else
    deletions=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('deletions',0))" 2>/dev/null)
    changed_files=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('changed_files',0))" 2>/dev/null)
    title=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('title',''))" 2>/dev/null)
    total=$((additions + deletions))
    echo "${repo},${pr},\"${title}\",${additions},${deletions},${total},${changed_files}"
  fi
  sleep 1
done
