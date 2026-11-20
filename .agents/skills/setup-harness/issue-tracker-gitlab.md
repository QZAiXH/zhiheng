# GitLab Issues

The selected tracker is `https://<host>/<namespace>/<project>`. Substitute the confirmed host and full namespace, including any subgroups. Pass `-R https://<host>/<namespace>/<project>` on issue commands across clones and worktrees. Pin the same host and project in API calls. Check the selection with `glab repo view https://<host>/<namespace>/<project>` when access is available.

- Publish the parent spec and each implementation ticket as separate issues with `glab issue create -R https://<host>/<namespace>/<project> --title '<title>' --description '<body>'`. Record the returned URL and project-scoped issue IID.
- Search all pages with `glab api --hostname '<host>' --paginate --method GET 'projects/<encoded-project-path>/issues' -f scope=all -f 'search=<goal or scenario terms>' -F per_page=100`. Render the full project path with each slash encoded as `%2F`, or use the verified numeric project ID. Omitting `state` includes opened and closed issues. After an uncertain create, repeat the search.
- Before the first create or such a retry, if search finds no match, confirm absence with the unfiltered project issue listing: `glab api --hostname '<host>' --paginate --method GET 'projects/<encoded-project-path>/issues' -f scope=all -F per_page=100`. Omit both `search` and `state` and run this check even if search returns zero. Page through the entire listing and compare the goal and scenario with candidate issues and their notes. Reuse a verified match. If a request, page or candidate read fails, or absence cannot be established, keep intake or retry pending.
- Read each candidate and its notes with `glab issue view <iid> -R https://<host>/<namespace>/<project> --comments` and follow its linked parent for the full acceptance criteria.
- Put `Part of #<parent>` in each child. Use a native blocking link when available, or record `Blocked by: #<iid>` in the description. Use a full issue URL for a different project.
- Append evidence and the acceptance decision with `glab issue note <iid> -R https://<host>/<namespace>/<project> --message '<text>'`. Outer acceptance posts the conclusion before `glab issue close <iid> -R https://<host>/<namespace>/<project>`.
- When triage is adopted, use `glab issue update <iid> -R https://<host>/<namespace>/<project> --label '<label>'` or `--unlabel '<label>'` with the agreed vocabulary.

MRs as a request surface: no. Preserve a project's existing opt-in. When enabled, read the MR body, notes and diff with the corresponding `glab mr` commands against the same explicit project.
