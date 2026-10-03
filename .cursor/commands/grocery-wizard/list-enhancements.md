# List enhancements

Show open items from the GitHub enhancement backlog.

## Context

- Backlog: GitHub Issues with the **`grocery-wizard`** label (legacy title matches may still appear during migration).
- Implement backlog items via **`/work-on-issue <number>`**.

## Your task

1. Run (requires **`gh`**):

```bash
gh issue list --label grocery-wizard --state open --limit 100 \
  --json number,title,labels,url \
  --jq '.[] | "#\(.number) | \(.title) | \(.url)"'
```

2. If the user asked for closed/done items too:

```bash
gh issue list --label grocery-wizard --state all --limit 100 \
  --json number,title,state,labels,url \
  --jq '.[] | "#\(.number) [\(.state)] | \(.title) | \(.url)"'
```

3. Present the output clearly (issue #, title, area from `gw-area-*` labels when present, link).

4. If there are open items, note: **`/work-on-issue <issue-number>`** to implement one.

Do not implement anything unless the user chooses an issue number and asks you to work on it in this chat.
