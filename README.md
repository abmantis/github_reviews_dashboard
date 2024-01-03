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

