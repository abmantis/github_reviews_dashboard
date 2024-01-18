# Description

This shows an overview of all the PRs in a repo and their review statuses. 

It works best with a flow where:
- reviewers always leave an approving review or request changes.
- authors always request a re-review from reviewers.

When that flow is used, knowing if a PR is waiting for your review is easy: just look for a ⚠️ sign! 

## Symbols

- ✉️: PR without a reviewed by you.
- ✅: PR with a review from you (either approving or requesting changes).
- ⚠️: PR with a (re-)review requested from you.
- ➡️: Your PR (also used as an aid to point out your name in the reviewrs list).


# Setup

```bash
git clone git@github.com:abmantis/github_reviews_dashboard.git
cd github_reviews_dashboard
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

# Usage

```bash
cd github_reviews_dashboard
source .venv/bin/activate
python dashboard.py --hostname $GITHUB_HOST --owner $REPO_OWNER --repository $REPO_NAME
```

You can also pass `--use-cli` to use Github CLI for requests.

Check other options with `python dashboard.py --help`.

