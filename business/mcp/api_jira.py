"""
MCP: api_jira
Tools for interacting with JIRA: creating, reading, updating issues and syncing backlogs.
"""
import logging
from typing import Optional

from langchain_core.tools import tool

from business.config import CONFIG

logger = logging.getLogger(__name__)


def _client():
    """Return an authenticated JIRA client."""
    try:
        from jira import JIRA  # type: ignore
    except ImportError:
        return None
    cfg = CONFIG.jira
    return JIRA(server=cfg.server, basic_auth=(cfg.user, cfg.api_token))


@tool
def create_jira_issue(
    summary: str,
    description: str,
    issue_type: str = "Story",
    priority: str = "Medium",
    labels: str = "",
) -> str:
    """Create a new JIRA issue (Story, Task, Bug, Epic, etc.).

    Args:
        summary: Issue title following the pattern '[ID] | ENTITY | ACTION | CONTEXT'.
        description: Full description with acceptance criteria.
        issue_type: JIRA issue type (Story, Task, Bug, Epic, Sub-task).
        priority: Priority level (Highest, High, Medium, Low, Lowest).
        labels: Comma-separated list of labels.

    Returns:
        Created issue key (e.g. 'PROJ-42').
    """
    jira = _client()
    if jira is None:
        return "ERROR: jira library not installed. Run: pip install jira"

    label_list = [l.strip() for l in labels.split(",") if l.strip()]
    issue_dict = {
        "project": {"key": CONFIG.jira.project_key},
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type},
        "priority": {"name": priority},
    }
    if label_list:
        issue_dict["labels"] = label_list

    issue = jira.create_issue(fields=issue_dict)
    return str(issue.key)


@tool
def get_jira_issue(issue_key: str) -> str:
    """Retrieve the full details of a JIRA issue.

    Args:
        issue_key: JIRA issue key (e.g. 'PROJ-42').

    Returns:
        Formatted string with issue details.
    """
    jira = _client()
    if jira is None:
        return "ERROR: jira library not installed."

    issue = jira.issue(issue_key)
    fields = issue.fields
    return (
        f"Key: {issue.key}\n"
        f"Summary: {fields.summary}\n"
        f"Status: {fields.status.name}\n"
        f"Type: {fields.issuetype.name}\n"
        f"Priority: {fields.priority.name if fields.priority else 'N/A'}\n"
        f"Assignee: {fields.assignee.displayName if fields.assignee else 'Unassigned'}\n"
        f"Description:\n{fields.description or ''}"
    )


@tool
def update_jira_issue(issue_key: str, summary: str = "", description: str = "", status: str = "") -> str:
    """Update fields of an existing JIRA issue.

    Args:
        issue_key: JIRA issue key (e.g. 'PROJ-42').
        summary: New summary (leave empty to keep current).
        description: New description (leave empty to keep current).
        status: Target status for transition (e.g. 'In Progress', 'Done').

    Returns:
        Confirmation message.
    """
    jira = _client()
    if jira is None:
        return "ERROR: jira library not installed."

    issue = jira.issue(issue_key)
    update_fields = {}
    if summary:
        update_fields["summary"] = summary
    if description:
        update_fields["description"] = description
    if update_fields:
        issue.update(fields=update_fields)

    if status:
        transitions = jira.transitions(issue)
        for t in transitions:
            if t["name"].lower() == status.lower():
                jira.transition_issue(issue, t["id"])
                break

    return f"Issue {issue_key} updated."


@tool
def delete_jira_issue(issue_key: str) -> str:
    """Delete a JIRA issue permanently.

    Args:
        issue_key: JIRA issue key (e.g. 'PROJ-42').

    Returns:
        Confirmation message.
    """
    jira = _client()
    if jira is None:
        return "ERROR: jira library not installed."

    jira.issue(issue_key).delete()
    return f"Issue {issue_key} deleted."


@tool
def search_jira_issues(jql: str, max_results: int = 20) -> str:
    """Search JIRA issues using JQL.

    Args:
        jql: JQL query string (e.g. 'project=PROJ AND status="To Do"').
        max_results: Maximum number of results to return.

    Returns:
        Newline-separated list of matching issue keys and summaries.
    """
    jira = _client()
    if jira is None:
        return "ERROR: jira library not installed."

    issues = jira.search_issues(jql, maxResults=max_results)
    if not issues:
        return "No issues found."
    return "\n".join(f"{i.key}: {i.fields.summary}" for i in issues)


@tool
def add_comment_to_issue(issue_key: str, comment: str) -> str:
    """Add a comment to a JIRA issue.

    Args:
        issue_key: JIRA issue key.
        comment: Comment text (supports JIRA wiki markup).

    Returns:
        Confirmation message.
    """
    jira = _client()
    if jira is None:
        return "ERROR: jira library not installed."

    jira.add_comment(issue_key, comment)
    return f"Comment added to {issue_key}."


@tool
def get_project_backlog(project_key: str = "", max_results: int = 50) -> str:
    """Retrieve the backlog (open issues) for a JIRA project.

    Args:
        project_key: JIRA project key (defaults to configured project).
        max_results: Maximum number of issues to return.

    Returns:
        Formatted backlog list.
    """
    jira = _client()
    if jira is None:
        return "ERROR: jira library not installed."

    key = project_key or CONFIG.jira.project_key
    jql = f'project="{key}" AND statusCategory != Done ORDER BY created DESC'
    issues = jira.search_issues(jql, maxResults=max_results)
    if not issues:
        return "Backlog is empty."
    lines = [f"{i.key} [{i.fields.issuetype.name}] {i.fields.summary}" for i in issues]
    return "\n".join(lines)


def _board_id_for_project(jira, project_key: str) -> Optional[str]:
    """Return the first Scrum/Kanban board id for the given project key, or None."""
    try:
        boards = jira.boards(projectKeyOrID=project_key)
        return str(boards[0].id) if boards else None
    except Exception as exc:
        logger.warning("[JIRA] Could not retrieve boards for project '%s': %s", project_key, exc)
        return None


@tool
def list_sprints(project_key: str = "", state: str = "active") -> str:
    """List sprints for a JIRA project board.

    Args:
        project_key: JIRA project key (defaults to configured project).
        state: Sprint state filter: active, closed, or future.

    Returns:
        Formatted list of sprints with id, name and state.
    """
    jira = _client()
    if jira is None:
        return "ERROR: jira library not installed."

    key = project_key or CONFIG.jira.project_key
    board_id = _board_id_for_project(jira, key)
    if board_id is None:
        return f"No board found for project '{key}'."

    try:
        sprints = jira.sprints(board_id, state=state)
    except Exception as exc:
        return f"ERROR listing sprints: {exc}"

    if not sprints:
        return f"No {state} sprints found for project '{key}'."
    lines = [f"ID={s.id} | {s.name} | {s.state}" for s in sprints]
    return "\n".join(lines)


@tool
def create_sprint(name: str, project_key: str = "", start_date: str = "", end_date: str = "") -> str:
    """Create a new sprint on the default board of a JIRA project.

    Args:
        name: Sprint name (e.g. 'Sprint 5 — Authentication').
        project_key: JIRA project key (defaults to configured project).
        start_date: Optional ISO 8601 start date (e.g. '2025-05-01T00:00:00.000Z').
        end_date: Optional ISO 8601 end date.

    Returns:
        Created sprint id and name.
    """
    jira = _client()
    if jira is None:
        return "ERROR: jira library not installed."

    key = project_key or CONFIG.jira.project_key
    board_id = _board_id_for_project(jira, key)
    if board_id is None:
        return f"No board found for project '{key}'."

    try:
        kwargs: dict = {"name": name, "board_id": board_id}
        if start_date:
            kwargs["startDate"] = start_date
        if end_date:
            kwargs["endDate"] = end_date
        sprint = jira.create_sprint(**kwargs)
        return f"Sprint created. ID={sprint.id} | Name={sprint.name}"
    except Exception as exc:
        return f"ERROR creating sprint: {exc}"


@tool
def assign_issue_to_sprint(issue_key: str, sprint_id: str) -> str:
    """Move a JIRA issue to a specific sprint.

    Args:
        issue_key: JIRA issue key (e.g. 'PROJ-42').
        sprint_id: Id of the target sprint (use list_sprints to find it).

    Returns:
        Confirmation message.
    """
    jira = _client()
    if jira is None:
        return "ERROR: jira library not installed."

    try:
        jira.add_issues_to_sprint(sprint_id, [issue_key])
        return f"Issue {issue_key} moved to sprint {sprint_id}."
    except Exception as exc:
        return f"ERROR assigning issue to sprint: {exc}"


JIRA_TOOLS = [
    create_jira_issue,
    get_jira_issue,
    update_jira_issue,
    delete_jira_issue,
    search_jira_issues,
    add_comment_to_issue,
    get_project_backlog,
    list_sprints,
    create_sprint,
    assign_issue_to_sprint,
]
