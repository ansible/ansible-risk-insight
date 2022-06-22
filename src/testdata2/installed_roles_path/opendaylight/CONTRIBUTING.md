# Contributing to the OpenDaylight Ansible Role

We work to make contributing easy. Please let us know if you spot something we can do better.

#### Table of Contents

1. [Overview](#overview)
2. [Communication](#communication)
   - [Issues](#issues)
   - [IRC channel](#irc-channel)
3. [Patches](#patches)

## Overview

We use [GitHub Issues][1] for most communication, including bug reports, feature requests and questions.

We accept patches via [GitHub Pull Requests][2]. Please fork our repo, make your changes, commit them to a feature branch and *submit a PR to have it merged back into this project*. We'll give feedback and get it merged ASAP.

## Communication

*Please use public, documented communication instead of reaching out to developers 1-1.*

Open Source projects benefit from always communicating in the open. Previously answered questions end up becoming documentation for other people hitting similar issues. More eyes may get your question answered faster. Doing everything in the open keeps community members on an equal playing field (`@<respected company>` email addresses don't get priority, good questions do).

We prefer [Issues][1] for most communication.

### Issues

Please use our [GitHub Issues][1] freely, even for small things! They are the primary method by which we track what's going on in the project.

The labels assigned to an issue can tell you important things about it.

For example, issues tagged [`good-for-beginners`][3] are likely to not require much background knowledge and be fairly self-contained, perfect for people new to the project who are looking to get involved.

The priority-related issue labels ([`prio:high`][4], [`prio:normal`][5]...) are also important to note. They typically accurately reflect the next TODOs the community will complete.

The `info:progress` labels may not always be up-to-date, but will be used when appropriate (typically long-standing issues that take multiple commits).

Issues can be referenced and manipulated from git commit messages. Just referencing the issue's number (`#42`) will link the commit and issue. Issues can also be closed from commit messages with `closes #42` (and [a variety of other key words][6]).

### IRC channel

Feel free to join us at **#opendaylight-integration** on `chat.freenode.net`. You can also use web client for Freenode to join us at [webchat][10].

## Patches

Please use [Pull Requests][2] to submit patches.

Basics of a pull request:

- Use the GitHub web UI to fork our repo.
- Clone your fork to your local system.
- Make your changes.
- Commit your changes, using a [good commit message][8] and referencing any applicable issues.
- Push your commit.
- Submit a pull request against the project, again using GitHub's web UI.
- We'll give feedback and get your changed merged ASAP.
- You contributed! [Thank you][9]!

Other tips for submitting excellent pull requests:

- If you'd like to make more than one logically distinct change, please submit them as different pull requests (if they don't depend on each other) or different commits in the same PR (if they do).
- If your PR contains a number of commits that provide one logical change, please squash them using `git rebase`.
- If applicable, please provide documentation updates to reflect your changes.

[1]: https://github.com/dfarrell07/ansible-opendaylight/issues

[2]: https://github.com/dfarrell07/ansible-opendaylight/pulls

[3]: https://github.com/dfarrell07/ansible-opendaylight/labels/good-for-beginners

[4]: https://github.com/dfarrell07/ansible-opendaylight/labels/prio%3Ahigh

[5]: https://github.com/dfarrell07/ansible-opendaylight/labels/prio%3Anormal

[6]: https://help.github.com/articles/closing-issues-via-commit-messages/

[8]: http://chris.beams.io/posts/git-commit/

[9]: http://cdn3.volusion.com/74gtv.tjme9/v/vspfiles/photos/Delicious%20Dozen-1.jpg

[10]: http://webchat.freenode.net/?channels=opendaylight-integration
