# Pre-publish checklist

Run these checks before you make the repository public, and again before each push.
Goal: no API keys and no personal data in files, logs, or git history.

All commands run from the repository root.

## 1. No API key in the current files

Real Anthropic keys start with `sk-ant-` and are long.
The tests use short fake keys on purpose, so we search for long ones only.

```bash
git grep -nE "sk-ant-[A-Za-z0-9_-]{40,}" -- . || echo "OK: no long sk-ant- keys in tracked files"
```

Also search files that git does not track yet:

```bash
grep -rnE "sk-ant-[A-Za-z0-9_-]{40,}" --exclude-dir=.git --exclude-dir=.venv . || echo "OK: none in the folder"
```

## 2. No API key in the git history

A key that was committed once stays in history, even if you delete the file later.

```bash
git log -p --all | grep -nE "sk-ant-[A-Za-z0-9_-]{40,}" || echo "OK: no keys in history"
```

## 3. `.env` and `logs/` are not tracked

```bash
git ls-files | grep -E "(^|/)\.env$|^logs/|^reports/" || echo "OK: .env, logs/, reports/ are not tracked"
git check-ignore -v .env logs/example.jsonl reports/example.md
```

The second command should print a `.gitignore` rule for each path.

## 4. Logs and reports in `docs/case-studies/` are masked

Case studies copy parts of real logs. Check them by hand and with grep:

```bash
grep -rnE "sk-ant-|x-api-key:|Bearer |anthropic-organization-id|wrkspc_" docs/case-studies/ || echo "OK: nothing found"
```

Also read each case study once. Check that there is no prompt text, no customer name, and no email address.

## 5. Personal data in files

Look for email addresses and review each hit:

```bash
git grep -nE "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" -- . || echo "OK: no email addresses in files"
```

Expected hits: none, or only `noreply` addresses.

## 6. Author emails in the git history

Every commit stores an author name and email. On a public repository, anyone can see them.

```bash
git log --all --format='%an <%ae> | committer: %cn <%ce>' | sort -u
```

Each line should show a `noreply` address, not a personal one.

### How to keep your email private from now on

1. On GitHub, open **Settings → Emails**.
2. Turn on **Keep my email addresses private**.
3. Turn on **Block command line pushes that expose my email**.
4. Use the noreply address that GitHub shows there (it looks like `12345678+username@users.noreply.github.com`).

### If an old commit already has a personal email

You can rewrite the commit and replace the email. This changes commit IDs, so `main` must be force-pushed.

- Do it early. It is easy while there are few commits.
- Copies that someone made before the rewrite still have the old email.
- GitHub may keep the old commit reachable by its direct URL for some time. To remove it fully, contact GitHub Support.

## 7. Turn on GitHub secret protection

On GitHub, open **Settings → Code security** (the name can change) and turn on:

- **Secret scanning**: GitHub warns you when a key is in the repository.
- **Push protection**: GitHub blocks a push that contains a known key format.

## 8. If a key leaked

1. **Revoke the key first** in the Claude Console. Deleting the file is not enough. The key is already public.
2. Create a new key.
3. Then clean the history and push again.
4. Check the Console usage page for requests you did not make.

## 9. Final look

- [ ] Steps 1–5 print "OK" (or every hit was reviewed and is safe).
- [ ] Step 6 shows only noreply addresses, or you decided to accept the old one.
- [ ] Secret scanning and push protection are on.
- [ ] `README.md` says this is a personal learning project.
