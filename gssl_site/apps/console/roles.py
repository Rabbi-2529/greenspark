"""
Who may do what in the console.

Three roles, held as Django groups so they can be reassigned without a deploy:

    EDITOR          change content, but not publish it
    PUBLISHER       everything an editor can do, plus publish and delete
    ADMINISTRATOR   everything, plus staff accounts and site settings

Ranks are compared with ``>=``, so a publisher can do an editor's work and an
administrator can do anyone's. A superuser always ranks as an administrator.

A staff account with no group ranks as VIEWER: it can sign in and read, and
change nothing. That is the deliberate default for a new account, so creating
one never hands out write access by accident.
"""

VIEWER = 0
EDITOR = 1
PUBLISHER = 2
ADMINISTRATOR = 3

EDITOR_GROUP = "Editors"
PUBLISHER_GROUP = "Publishers"
ADMINISTRATOR_GROUP = "Administrators"

# Group name -> rank. The only place the mapping is written down.
GROUP_RANKS = {
    EDITOR_GROUP: EDITOR,
    PUBLISHER_GROUP: PUBLISHER,
    ADMINISTRATOR_GROUP: ADMINISTRATOR,
}

RANK_LABELS = {
    VIEWER: "Read only",
    EDITOR: "Editor",
    PUBLISHER: "Publisher",
    ADMINISTRATOR: "Administrator",
}


def rank_of(user) -> int:
    """The highest rank any of the user's groups grants."""
    if not user or not user.is_authenticated:
        return VIEWER
    if user.is_superuser:
        return ADMINISTRATOR
    names = {group.name for group in user.groups.all()}
    return max((GROUP_RANKS[name] for name in names if name in GROUP_RANKS), default=VIEWER)


def has_rank(user, needed: int) -> bool:
    return rank_of(user) >= needed


def label_of(user) -> str:
    return RANK_LABELS[rank_of(user)]


def may_sign_in(user) -> bool:
    """The console is for staff accounts only, and only while they are active."""
    return bool(user and user.is_authenticated and user.is_active and user.is_staff)
