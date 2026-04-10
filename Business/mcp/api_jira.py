"""
MCP: api_jira
Tools for interacting with JIRA: creating, reading, updating issues and syncing backlogs.
"""
import logging
from typing import Optional

from langchain_core.tools import tool

from Business.config import CONFIG

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
    project_key: str = "",
    team_id: str = "",
    story_points: float = 0,
    epic_link: str = "",
    parent_key: str = "",
) -> str:
    """Create a new JIRA issue (Story, Task, Bug, Epic, Sub-task).

    Args:
        summary: Issue title following the pattern '[ID] | ENTITY | ACTION | CONTEXT'.
        description: Full description with acceptance criteria (JIRA wiki markup supported).
        issue_type: JIRA issue type (Story, Task, Bug, Epic, Sub-task).
        priority: Priority level (Highest, High, Medium, Low, Lowest).
        labels: Comma-separated list of labels.
        project_key: JIRA project key (defaults to first configured project).
        team_id: Numeric Team ID (required when the project enforces a Team field).
                 Falls back to JIRA_TEAM_ID env var when omitted.
        story_points: Story point estimate (Fibonacci: 1, 2, 3, 5, 8, 13). 0 = not set.
        epic_link: Epic key to link this story to (classic JIRA, e.g. 'ORC-10').
        parent_key: Parent issue key (next-gen projects / sub-tasks).

    Returns:
        Created issue key (e.g. 'PROJ-42').
    """
    jira = _client()
    if jira is None:
        return "ERROR: jira library not installed. Run: pip install jira"

    label_list = [l.strip() for l in labels.split(",") if l.strip()]
    issue_dict = {
        "project": {"key": project_key or CONFIG.jira.project_key},
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type},
        "priority": {"name": priority},
    }
    if label_list:
        issue_dict["labels"] = label_list

    resolved_team_id = team_id or CONFIG.jira.team_id
    if resolved_team_id:
        # Jira Cloud Advanced Roadmaps: team UUID passed as a plain string value
        issue_dict["customfield_10001"] = str(resolved_team_id)

    if story_points and story_points > 0:
        # customfield_10016 = Story Points in most JIRA Cloud instances
        issue_dict["customfield_10016"] = story_points
        issue_dict["story_points"] = story_points  # fallback for some configs

    if parent_key:
        issue_dict["parent"] = {"key": parent_key}
    elif epic_link:
        # Classic JIRA: customfield_10008 / Next-gen: parent field
        issue_dict["customfield_10008"] = epic_link

    try:
        issue = jira.create_issue(fields=issue_dict)
        return str(issue.key)
    except Exception as exc:
        error_msg = str(exc)
        if "Team" in error_msg or "customfield_10001" in error_msg:
            return (
                f"ERROR ao criar issue no JIRA: {error_msg}\n"
                "Dica: configure JIRA_TEAM_ID no .env com o ID numérico do seu Team "
                "(visível em: JIRA > Project Settings > Teams, ou no URL do team)."
            )
        return f"ERROR ao criar issue no JIRA: {error_msg}"


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


def _resolve_account_id(jira, email: str) -> str:
    """Resolve a Jira Cloud accountId from an email address."""
    try:
        users = jira.search_users(query=email)
        for u in users:
            if getattr(u, "emailAddress", "").lower() == email.lower():
                return u.accountId
        if users:
            return users[0].accountId
    except Exception as exc:
        logger.warning("[JIRA] Could not resolve accountId for %s: %s", email, exc)
    return email  # fall back to raw email


@tool
def search_jira_issues(jql: str, max_results: int = 0) -> str:
    """Search JIRA issues using JQL.

    Args:
        jql: JQL query string (e.g. 'project=PROJ AND status="To Do"').
        max_results: Maximum number of results to return. Capped at 50 to prevent
                 hanging on large projects. Use keyword-filtered JQL instead of
                 fetching all issues.

    Returns:
        Newline-separated list of matching issue keys and summaries.
    """
    jira = _client()
    if jira is None:
        return "ERROR: jira library not installed."

    # Replace email addresses in JQL with Jira Cloud accountId
    import re as _re
    emails_found = _re.findall(
        r'=\s*["\']?([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})["\']?',
        jql,
    )
    for email in emails_found:
        account_id = _resolve_account_id(jira, email)
        jql = _re.sub(
            r'=\s*["\']?' + _re.escape(email) + r'["\']?',
            f'= "{account_id}"',
            jql,
        )

    # When max_results=0, paginate and fetch all results (may be slow on large projects;
    # always use keyword-filtered JQL to avoid timeouts).
    limit = False if max_results == 0 else max_results
    try:
        issues = jira.search_issues(jql, maxResults=limit)
    except Exception as exc:
        return f"Search failed: {exc}. Proceed without duplicate check."
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
def get_project_backlog(project_key: str = "", max_results: int = 0) -> str:
    """Retrieve ALL issues for a JIRA project.

    Args:
        project_key: JIRA project key (defaults to configured project).
        max_results: Maximum number of issues to return. 0 (default) returns ALL issues.

    Returns:
        Formatted backlog list.
    """
    jira = _client()
    if jira is None:
        return "ERROR: jira library not installed."

    key = project_key or CONFIG.jira.project_key
    jql = f'project="{key}" ORDER BY created DESC'
    limit = False if max_results == 0 else max_results
    issues = jira.search_issues(jql, maxResults=limit)
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


@tool
def get_my_issues(
    project_key: str = "",
    status: str = "",
    max_results: int = 50,
) -> str:
    """List JIRA issues assigned to the currently configured user (currentUser()).

    Uses Jira's currentUser() function — the most reliable way to find issues
    assigned to the authenticated user regardless of email/accountId format.

    Args:
        project_key: Optional project key to filter (e.g. 'ORC'). Leave empty for all projects.
        status: Optional status filter (e.g. 'In Progress', 'To Do'). Leave empty for all.
        max_results: Maximum number of results to return.

    Returns:
        Formatted list of issues.
    """
    jira = _client()
    if jira is None:
        return "ERROR: jira library not installed."

    conditions = ["assignee = currentUser()"]
    if project_key:
        conditions.append(f'project = "{project_key}"')
    if status:
        conditions.append(f'status = "{status}"')
    jql = " AND ".join(conditions) + " ORDER BY updated DESC"

    try:
        issues = jira.search_issues(jql, maxResults=max_results)
        if not issues:
            return "No issues found assigned to you."
        lines = []
        for i in issues:
            assignee = getattr(i.fields.assignee, "displayName", "Unassigned") if i.fields.assignee else "Unassigned"
            status_name = getattr(i.fields.status, "name", "?")
            lines.append(f"{i.key} [{status_name}]: {i.fields.summary}")
        return "\n".join(lines)
    except Exception as exc:
        return f"ERROR searching issues: {exc}"


@tool
def create_complete_story(
    summary: str,
    description: str,
    priority: str = "Medium",
    labels: str = "",
    project_key: str = "",
    team_id: str = "",
    story_points: float = 0,
    epic_link: str = "",
    subtasks: str = "",
) -> str:
    """Create a full User Story with optional sub-tasks in a single operation.

    Use this tool for engineering-grade stories (points >= 5) that need decomposition
    into sub-tasks. Creates the parent story first, then all sub-tasks linked to it.

    Args:
        summary: Story title following '[ID] | ENTITY | ACTION | CONTEXT'.
        description: Full rich description in JIRA wiki markup (narrative, AC, NFR, DoD, etc.).
        priority: Priority level (Highest, High, Medium, Low, Lowest).
        labels: Comma-separated labels.
        project_key: JIRA project key (defaults to configured project).
        team_id: Team ID — falls back to JIRA_TEAM_ID env var.
        story_points: Story point estimate (Fibonacci: 1, 2, 3, 5, 8, 13). 0 = not set.
        epic_link: Epic key to link this story to (e.g. 'ORC-10').
        subtasks: Pipe-separated list of sub-task summaries to create under this story.
                  Example: "Backend API endpoint|Frontend component|Unit tests|Docs update"
                  Leave empty to skip sub-task creation.

    Returns:
        Created story key and list of sub-task keys.
    """
    # 1. Create the parent story
    story_key = create_jira_issue.invoke({
        "summary": summary,
        "description": description,
        "issue_type": "Story",
        "priority": priority,
        "labels": labels,
        "project_key": project_key,
        "team_id": team_id,
        "story_points": story_points,
        "epic_link": epic_link,
    })

    if story_key.startswith("ERROR"):
        return story_key

    results = [f"Story created: {story_key}"]

    # 2. Create sub-tasks if provided
    if subtasks:
        task_summaries = [t.strip() for t in subtasks.split("|") if t.strip()]
        created_subtasks = []
        failed_subtasks = []
        for task_summary in task_summaries:
            sub_key = create_jira_issue.invoke({
                "summary": task_summary,
                "description": f"Sub-task of [{story_key}]\n\n{task_summary}",
                "issue_type": "Sub-task",
                "priority": priority,
                "labels": labels,
                "project_key": project_key or CONFIG.jira.project_key,
                "team_id": team_id,
                "parent_key": story_key,
            })
            if sub_key.startswith("ERROR"):
                failed_subtasks.append(f"{task_summary}: {sub_key}")
            else:
                created_subtasks.append(sub_key)

        if created_subtasks:
            results.append(f"Sub-tasks created: {', '.join(created_subtasks)}")
        if failed_subtasks:
            results.append(f"Sub-tasks failed:\n" + "\n".join(failed_subtasks))

    return "\n".join(results)


JIRA_TOOLS = [
    create_jira_issue,
    create_complete_story,
    get_jira_issue,
    update_jira_issue,
    delete_jira_issue,
    search_jira_issues,
    get_my_issues,
    add_comment_to_issue,
    get_project_backlog,
    list_sprints,
    create_sprint,
    assign_issue_to_sprint,
]
