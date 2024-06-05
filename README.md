# Description

This shows an overview of all the PRs in a repo and their review statuses. 

It works best with a flow where:
- reviewers always leave an approving review or request changes.
- authors always request a re-review from reviewers when ready.

When that flow is used, knowing if a PR is waiting for your review is easy: just look for a ⚠️ sign! 

## Symbols

- ✉️: PR without a reviewed by you.
- ✅: PR with a review from you (either approving or requesting changes).
- ⚠️: PR with a (re-)review requested from you.
- ➡️: Your PR (also used as an aid to point out your name in the reviewrs list).


# Setup

```bash
pip install git+https://github.com/abmantis/github_reviews_dashboard
```

# Usage

```bash
github-reviews-dashboard --hostname $GITHUB_HOST --owner $REPO_OWNER --repository $REPO_NAME
```

You can also pass `--use-cli` to use Github CLI for requests.

Check other options with `python dashboard.py --help`.

