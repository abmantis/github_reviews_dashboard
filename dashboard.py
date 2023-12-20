import argparse
import subprocess
import json
from enum import Enum
from dataclasses import dataclass
import datetime

BOLD_STYLE = "\033[1m"
GREEN_STYLE = "\033[92m"
ORANGE_STYLE = "\033[93m"
GREY_STYLE = "\033[90m"
RESET_STYLE = "\033[0m"


class ReviewStatus(Enum):
    APPROVED = 1
    CHANGES_REQUESTED = 2
    COMMENTED = 3
    DISMISSED = 4
    PENDING = 5


def to_review_status(status: str):
    if status == "APPROVED":
        return ReviewStatus.APPROVED
    elif status == "CHANGES_REQUESTED":
        return ReviewStatus.CHANGES_REQUESTED
    elif status == "COMMENTED":
        return ReviewStatus.COMMENTED
    elif status == "DISMISSED":
        return ReviewStatus.DISMISSED
    else:
        return ReviewStatus.PENDING


@dataclass
class User:
    login: str
    name: str


@dataclass
class ReviewState:
    user: User
    status: ReviewStatus
    when: datetime.datetime


@dataclass
class Label:
    name: str
    color: str


@dataclass
class PullRequest:
    number: int
    title: str
    url: str
    isDraft: bool
    labels: list[Label]
    author: User
    review_states: list[ReviewState]


def rgb_to_ansi(rgb: str):
    r, g, b = rgb[:2], rgb[2:4], rgb[4:]
    return f"\033[38;2;{int(r, 16)};{int(g, 16)};{int(b, 16)}m"


def rgb_to_ansi_background(rgb: str):
    r, g, b = rgb[:2], rgb[2:4], rgb[4:]
    return f"\033[48;2;{int(r, 16)};{int(g, 16)};{int(b, 16)}m"


def review_status_to_emoji(status: ReviewStatus):
    if status == ReviewStatus.APPROVED:
        return "🟢"
    elif status == ReviewStatus.CHANGES_REQUESTED:
        return "🔴"
    elif status == ReviewStatus.COMMENTED or status == ReviewStatus.DISMISSED:
        return "💬"
    else:
        return "⚠️ "


def get_user_display_name(user: User):
    if user.name is not None:
        return user.name
    return user.login


def do_query(query, hostname):
    """Use github cli to do a graphql query."""
    try:
        return json.loads(
            subprocess.check_output(
                [
                    "gh",
                    "api",
                    "graphql",
                    "--hostname",
                    f"{hostname}",
                    "-f",
                    f"query={query}",
                ]
            ).decode("utf-8")
        )
    except subprocess.CalledProcessError:
        print("Error while executing query")
        exit(1)


def fetch_data(hostname: str, repository: str, owner: str):
    query = f"""
        query {{
            viewer {{
                login
            }}
            repository(owner: "{owner}", name: "{repository}") {{
                pullRequests(last: 100, states: OPEN) {{
                    nodes {{
                        number
                        title
                        url
                        isDraft
                        labels(first: 100) {{
                            nodes {{
                                name
                                color
                            }}
                        }}
                        author {{
                            login
                            ... on User {{
                                name
                            }}
                        }}
                        latestReviews(last: 100) {{
                            nodes {{
                                author {{
                                    ... on User {{
                                        login
                                        name
                                    }}
                                }}
                                state
                                createdAt
                            }}
                        }}
                        reviewRequests(last: 100) {{
                            nodes {{
                                requestedReviewer {{
                                    ... on User {{
                                        login
                                        name
                                    }}
                                }}
                            }}
                        }}
                        timelineItems(itemTypes: REVIEW_REQUESTED_EVENT, last: 100) {{
                            nodes {{
                                ... on ReviewRequestedEvent {{
                                    createdAt
                                    requestedReviewer {{
                                        ... on User {{
                                            login
                                            name
                                        }}
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
    """
    return do_query(query, hostname)


def parse_review_states(pr_node: dict):
    states = {
        review["requestedReviewer"]["login"]: ReviewState(
            when=datetime.datetime.strptime(review["createdAt"], "%Y-%m-%dT%H:%M:%SZ"),
            user=User(
                login=review["requestedReviewer"]["login"],
                name=review["requestedReviewer"]["name"],
            ),
            status=ReviewStatus.PENDING,
        )
        for review in pr_node["timelineItems"]["nodes"]
        if "requestedReviewer" in review
        and review["requestedReviewer"] is not None
        and "login" in review["requestedReviewer"]
    }

    for review in pr_node["latestReviews"]["nodes"]:
        if "login" not in review["author"]:
            continue
        user = User(login=review["author"]["login"], name=review["author"]["name"])
        states[user.login] = ReviewState(
            when=datetime.datetime.strptime(review["createdAt"], "%Y-%m-%dT%H:%M:%SZ"),
            user=user,
            status=to_review_status(review["state"]),
        )

    return sorted(states.values(), key=lambda state: state.user.login)


def parse_pull_requests(pr_nodes: list[dict]):
    return [
        PullRequest(
            number=pr["number"],
            title=pr["title"],
            url=pr["url"],
            isDraft=pr["isDraft"],
            labels=[
                Label(label["name"], label["color"]) for label in pr["labels"]["nodes"]
            ],
            author=User(login=pr["author"]["login"], name=pr["author"]["name"]),
            review_states=parse_review_states(pr),
        )
        for pr in pr_nodes
    ]


def get_pr_user_review_state(pr: PullRequest, user_login: str) -> ReviewState | None:
    for review_state in pr.review_states:
        if review_state.user.login == user_login:
            return review_state
    return None


def get_pr_indicator(pr: PullRequest, user_login: str):
    if pr.author.login == user_login:
        return "🞂 "

    review_state = get_pr_user_review_state(pr, user_login)
    if review_state is None:
        return "🆕"
    if review_state.status == ReviewStatus.PENDING:
        return review_status_to_emoji(review_state.status)
    return "✅"


def print_reviewers_for_pr(pr: PullRequest, user_login: str):
    for review_state in pr.review_states:
        indicator = "🞂" if review_state.user.login == user_login else " "
        review_emoji = f"{review_status_to_emoji(review_state.status)} "
        reviewer_display_name = get_user_display_name(review_state.user)

        time_diff = round(
            (datetime.datetime.now() - review_state.when).total_seconds() / 60 / 60
        )

        reviewer_highlight_str = ""
        if review_state.user.login == user_login:
            if review_state.status == ReviewStatus.PENDING:
                reviewer_highlight_str = f"{BOLD_STYLE}{ORANGE_STYLE}"
            else:
                reviewer_highlight_str = GREEN_STYLE
        print(
            f"  {indicator} {review_emoji}"
            f" {reviewer_highlight_str}{reviewer_display_name}"
            f" ({time_diff}h ago){RESET_STYLE}"
        )
    print()


def print_pull_requests(
    pull_requests: list[PullRequest], user_login: str, print_reviewers: bool = True
):
    for pr in pull_requests:
        labels_str = " ".join(
            [
                f"{rgb_to_ansi_background(label.color)}{label.name}{RESET_STYLE}"
                for label in pr.labels
            ]
        )
        author_style = GREEN_STYLE if pr.author.login == user_login else ""
        author_str = f"{author_style}[{get_user_display_name(pr.author)}]{RESET_STYLE}"

        print(
            f"{BOLD_STYLE}{get_pr_indicator(pr, user_login)}"
            f" #{pr.number}: {pr.title}{RESET_STYLE} {author_str} {labels_str}"
        )
        print(f"   {GREY_STYLE}{pr.url}{RESET_STYLE}")

        if print_reviewers:
            print_reviewers_for_pr(pr, user_login)


def print_user_stats(pull_requests: list[PullRequest], user_login: str):
    viewer_review_states: list[ReviewState] = []
    viewer_no_review_count = 0
    viewer_is_author_count = 0

    for pr in pull_requests:
        user_is_author = pr.author.login == user_login
        user_is_reviewer = False

        for review_state in pr.review_states:
            if review_state.user.login == user_login:
                user_is_reviewer = True
                viewer_review_states.append(review_state)

        if user_is_author:
            viewer_is_author_count += 1
        elif not user_is_reviewer:
            viewer_no_review_count += 1

    viewer_pending_review_count = len(
        [
            state
            for state in viewer_review_states
            if state.status == ReviewStatus.PENDING
        ]
    )
    viewer_reviewed_count = len(
        [
            state
            for state in viewer_review_states
            if state.status != ReviewStatus.PENDING
        ]
    )

    pending_review_style = (
        ORANGE_STYLE + BOLD_STYLE if viewer_pending_review_count > 0 else ""
    )
    print()
    print(
        f"∑ {viewer_is_author_count} author | {viewer_reviewed_count} reviewed | "
        f"{viewer_no_review_count} not reviewed | "
        f"{pending_review_style}{viewer_pending_review_count} pending review{RESET_STYLE}"
    )
    print()


parser = argparse.ArgumentParser(description="Github Pull Request Dashboard")
parser.add_argument("--hostname", help="Github hostname", default="github.com")
parser.add_argument("--owner", help="Github repository owner", required=True)
parser.add_argument("--repository", help="Github repository", required=True)
parser.add_argument(
    "--show-drafts", help="Show draft pull requests", action="store_true"
)
args = parser.parse_args()

github_data = fetch_data(args.hostname, args.repository, args.owner)
viewer_login = github_data["data"]["viewer"]["login"]

pull_requests = parse_pull_requests(
    github_data["data"]["repository"]["pullRequests"]["nodes"]
)

if not args.show_drafts:
    pull_requests = [pr for pr in pull_requests if not pr.isDraft]

print_pull_requests(pull_requests, viewer_login)
print_user_stats(pull_requests, viewer_login)
