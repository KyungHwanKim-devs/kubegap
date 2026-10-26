# Security policy

kubegap is a read-only audit tool. Two kinds of problem need two different channels.

## Report privately: exploitable defects

A defect that someone could use against a cluster or its operator before it is fixed. For example: a crafted object name, label or log line that makes a collected command run something else; a code path that reads a Secret value or writes one to disk; cluster data leaving the machine through a channel other than the user's own coding agent session.

Use GitHub's private vulnerability reporting: open the **Security** tab and choose **Report a vulnerability**. Include the kubegap version, the rubric version printed at the bottom of the report, the platform, and the smallest snapshot excerpt that reproduces it. Mask names first. The report stays private until the fix is released, then it is published with credit.

## Open an issue: hardening

Everything that makes the read-only promise tighter but is not an attack in itself: permission scope in `deploy/permissions/`, defaults that could be safer, data the audit collects that it does not need, documentation that overstates what the tool does. These are ordinary issues and pull requests, and they are welcome in public. Use the **Hardening** issue form.

## Supported versions

Only the latest release is supported.
