# find-prs

Discover and filter GitHub PRs suitable for SWE-bench evaluation.

## Usage

```
/find-prs [--min-lines N] [--min-files N] [--output FILE]
```

## Examples

```
# Default: >150 lines, >5 files
/find-prs

# Custom thresholds
/find-prs --min-lines 200 --min-files 10

# Save to file
/find-prs --output my_prs.csv
```

## How it works

1. Runs `fetch_prs.sh` against a curated list of repos/PRs
2. Filters by:
   - **Blacklist**: Skips repos in `/home/ubuntu/data/github/黑名单.text` (7000+ repos)
   - **Lines**: Total changes (additions + deletions) must exceed threshold
   - **Files**: Changed files count must exceed threshold
3. Fetches PR details via GitHub API (title, additions, deletions, changed_files)
4. Outputs CSV: `repo,PR#,title,additions,deletions,total,changed_files`

## Output Format

```csv
rust-lang/rust,157656,"Rollup of 7 pull requests",694,172,866,40
kubernetes/kubernetes,139579,"Promote PodCertificate...",8149,1026,9175,68
```

## Requirements

- `fetch_prs.sh` script
- GitHub API access (rate limited, uses `curl`)
- Blacklist file at `/home/ubuntu/data/github/黑名单.text`
