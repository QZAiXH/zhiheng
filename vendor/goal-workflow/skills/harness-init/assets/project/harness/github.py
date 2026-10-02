"""Bounded GitHub CLI adapter. Read failures never imply empty dependencies/success.

REST contracts: https://docs.github.com/en/rest/issues/issue-dependencies
https://docs.github.com/en/rest/checks/runs ; https://cli.github.com/manual/gh_pr_merge
Native dependency support is explicit: a 404 is NOT a capability probe.
"""
from graphlib import TopologicalSorter, CycleError
import time
import hashlib
import json
import re
import subprocess
import math
import uuid
from pathlib import Path
from urllib.parse import quote, urlparse


class AdapterError(RuntimeError):
    pass


def controlled_runner(controller):
    """Production bridge: native gh must share lock, process journal and budget."""
    def run(argv, timeout):
        token = 'gh-' + uuid.uuid4().hex
        output = controller.common / 'harness-github' / (token + '.stdout')
        record = controller.execute(argv, controller.root, token, output, timeout=timeout,
                                    scope='github', separate_stderr=True)
        stdout = output.read_text()
        stderr = Path(record['stderr_log']).read_text()
        if record['reason'] == 'timeout':
            raise subprocess.TimeoutExpired(argv, timeout, output=stdout, stderr=stderr)
        if record['reason']:
            raise AdapterError('Controlled GitHub operation stopped: ' + record['reason'])
        return subprocess.CompletedProcess(argv, record['exit_code'], stdout, stderr)
    return run


class GitHubAdapter:
    capabilities = {'native_dependencies': True, 'pull_requests': True,
                    'checks': True, 'merge_constraints': True}

    def __init__(self, config, run=None):
        self.config = config
        self.repository = config.get('repository') or config.get('github', {}).get('repository')
        if not self.repository or not re.fullmatch(r'[\w.-]+/[\w.-]+', self.repository):
            raise AdapterError('GitHub repository must be owner/repo')
        server = config.get('hostname') or config.get('github', {}).get('server', 'github.com')
        self.hostname = urlparse(server).hostname if '://' in server else server
        self.timeout = config.get('timeouts', {}).get('github_query', config.get('limits', {}).get('request_seconds', 30))
        if type(self.timeout) not in (float, int) or not math.isfinite(self.timeout) or self.timeout <= 0:
            raise AdapterError('github_query timeout must be positive')
        self.run = run or self._run
        self.repo_arg = self.repository if self.hostname == 'github.com' else f'{self.hostname}/{self.repository}'

    @staticmethod
    def _run(argv, timeout):
        return subprocess.run(argv, timeout=timeout, capture_output=True, text=True)

    def _command(self, args, json_output=True):
        concatenate_pages = False
        try:
            timeout = self.timeout
            if getattr(self, '_deadline', None) is not None:
                timeout = min(timeout, self._deadline - time.monotonic())
                if timeout <= 0:
                    raise AdapterError('GitHub total query deadline exhausted')
            result = self.run(['gh', *args], timeout)
            if result.returncode and '--slurp' in args and re.search(r'unknown flag:\s*--slurp', result.stderr):
                # Older official gh supports --paginate but lacks --slurp. This
                # is a local option parse failure before any HTTP request.
                # Native pagination still runs; only frame its JSON pages here.
                retry_args = [arg for arg in args if arg != '--slurp']
                if getattr(self, '_deadline', None) is not None:
                    timeout = min(self.timeout, self._deadline - time.monotonic())
                    if timeout <= 0:
                        raise AdapterError('GitHub total query deadline exhausted')
                result = self.run(['gh', *retry_args], timeout)
                concatenate_pages = True
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AdapterError(f'GitHub query/operation outcome unknown: {type(exc).__name__}') from exc
        if result.returncode:
            raise AdapterError(f'GitHub command failed (exit={result.returncode}): {result.stderr.strip()}')
        if not json_output:
            return result.stdout.strip()
        try:
            if concatenate_pages:
                decoder = json.JSONDecoder()
                remaining = result.stdout.strip()
                pages = []
                while remaining:
                    page, consumed = decoder.raw_decode(remaining)
                    pages.append(page)
                    remaining = remaining[consumed:].lstrip()
                if not pages:
                    raise ValueError('empty paginated output')
                return pages
            return json.loads(result.stdout)
        except (ValueError, TypeError) as exc:
            raise AdapterError('GitHub returned invalid JSON') from exc

    def _api(self, endpoint, paginate=False):
        args = ['api', '--hostname', self.hostname, '-H', 'Accept: application/vnd.github+json',
                '-H', 'X-GitHub-Api-Version: 2022-11-28', endpoint]
        if paginate:
            args += ['--paginate', '--slurp']
        data = self._command(args)
        if paginate:
            if not isinstance(data, list) or not all(isinstance(p, list) for p in data):
                raise AdapterError('Malformed paginated GitHub response')
            return [item for page in data for item in page]
        return data

    def _issue(self, item, source=None):
        if not isinstance(item, dict) or not isinstance(item.get('number'), int):
            raise AdapterError('Malformed GitHub issue')
        repo = self.repository
        if item.get('repository_url'):
            repo = item['repository_url'].split('/repos/', 1)[-1]
        out = dict(id=f'github:{self.hostname}:{repo}#{item["number"]}', number=item['number'],
                   repository=repo, title=item.get('title', ''), body=item.get('body') or '',
                   state=item.get('state', 'unknown'), state_reason=item.get('state_reason'),
                   url=item.get('html_url'))
        if source:
            out['source'] = source
        return out

    def _identity(self, task_id):
        if isinstance(task_id, int) or str(task_id).isdigit():
            return self.repository, int(task_id)
        prefix = f'github:{self.hostname}:'
        value = str(task_id)
        if not value.startswith(prefix):
            raise AdapterError('Task identity belongs to a different mode/host')
        repo, number = value[len(prefix):].rsplit('#', 1)
        if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo) or not number.isdigit():
            raise AdapterError('Invalid GitHub task identity')
        return repo, int(number)

    def list_tasks(self):
        rows = self._api(f'repos/{self.repository}/issues?state=open&per_page=100', True)
        return [self._issue(row) for row in rows if 'pull_request' not in row]

    def read_task(self, task_id):
        repo, number = self._identity(task_id)
        return self._issue(self._api(f'repos/{repo}/issues/{number}'))

    def dependencies(self, task_id):
        repo, number = self._identity(task_id)
        task = self.read_task(task_id)
        found = {}
        if self.config.get('github', {}).get('native_dependencies', True):
            for row in self._api(f'repos/{repo}/issues/{number}/dependencies/blocked_by?per_page=100', True):
                dep = self._issue(row, 'native')
                found[dep['id']] = dep
        # Deliberately only parse dependency statements, not arbitrary issue mentions.
        for line in task['body'].splitlines():
            match = re.search(r'\b(?:dependencies\s*:|depends on\s*:?|requires\s*:?)\s*(.*)', line, re.I)
            if match:
                for dep_repo, dep_number in re.findall(r'(?:(\b[\w.-]+/[\w.-]+))?#(\d+)', match.group(1)):
                    dep = self.read_task(f'github:{self.hostname}:{dep_repo or repo}#{dep_number}')
                    dep['source'] = 'body'
                    found.setdefault(dep['id'], dep)
        return list(found.values())

    def dependency_graph(self):
        graph, tasks = {}, {}
        pending = list(self.list_tasks())
        while pending:
            task = pending.pop()
            key = task['id']
            if key in graph:
                continue
            tasks[key] = task
            deps = self.dependencies(key)
            graph[key] = [d['id'] for d in deps]
            pending.extend(d for d in deps if d['id'] not in graph)
        try:
            order = list(TopologicalSorter(graph).static_order())
        except CycleError as exc:
            raise AdapterError(f'Dependency cycle: {exc.args[1]}') from exc
        return {'tasks': tasks, 'dependencies': graph, 'order': order}

    @staticmethod
    def dependency_satisfied(task, delivery):
        # Issue closed (even completed) is not proof of delivered, verified content.
        return bool(delivery and delivery.get('status') == 'delivered' and
                    delivery.get('verified_delivery') is True and delivery.get('delivered_sha'))

    def find_pr(self, head, base):
        query = f'repos/{self.repository}/pulls?state=all&per_page=100&head={quote(head, safe="")}&base={quote(base, safe="")}'
        prs = self._api(query, True)
        matches = [p for p in prs if p.get('head', {}).get('label') == head
                   and p.get('base', {}).get('ref') == base]
        if len(matches) > 1:
            raise AdapterError('Multiple matching PRs: explicit PR identity required')
        return matches[0] if matches else None

    def read_pr(self, number):
        data = self._api(f'repos/{self.repository}/pulls/{int(number)}')
        if not isinstance(data, dict) or not isinstance(data.get('number'), int) or not data.get('head', {}).get('sha') or not data.get('base', {}).get('sha'):
            raise AdapterError('Malformed PR identity or refs')
        return data

    def branch_head(self, branch):
        """Resolve the branch itself: PR.base.sha can lag a real base advance."""
        if not isinstance(branch, str) or not branch or branch.startswith('-'):
            raise AdapterError('Explicit target branch name required')
        data = self._api(f'repos/{self.repository}/git/ref/heads/{quote(branch, safe="")}')
        sha = data.get('object', {}).get('sha') if isinstance(data, dict) else None
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', sha):
            raise AdapterError('Actual target branch ref missing or malformed')
        return sha

    def checks(self, number, expected_sha, required_names):
        if not required_names:
            raise AdapterError('Required checks must be explicitly configured')
        before = self.read_pr(number)
        # Use commit-addressed REST checks, never PR UI green with no checked SHA.
        pages = self._command(['api', '--hostname', self.hostname,
            f'repos/{self.repository}/commits/{expected_sha}/check-runs?per_page=100', '--paginate', '--slurp'])
        if not isinstance(pages, list) or not all(isinstance(p, dict) and isinstance(p.get('check_runs'), list) for p in pages):
            raise AdapterError('Malformed check-runs response')
        runs = [c for p in pages for c in p['check_runs']]
        status_pages = self._api(f'repos/{self.repository}/commits/{expected_sha}/statuses?per_page=100', True)
        checks = {}
        for c in sorted(runs, key=lambda c: c.get('id', 0)):
            if c.get('head_sha') != expected_sha:
                raise AdapterError('Check result SHA mismatch')
            checks[c.get('name')] = {'status': 'pass' if c.get('status') == 'completed' and c.get('conclusion') == 'success'
                                    else ('pending' if c.get('status') != 'completed' else 'fail'),
                                    'url': c.get('html_url'), 'sha': expected_sha}
        for c in status_pages:  # statuses endpoint is newest first
            if c.get('context') not in checks:
                checks[c.get('context')] = {'status': 'pass' if c.get('state') == 'success' else c.get('state', 'unknown'),
                                            'url': c.get('target_url'), 'sha': expected_sha}
        after = self.read_pr(number)
        if before.get('head', {}).get('sha') != after.get('head', {}).get('sha') or before.get('base', {}).get('sha') != after.get('base', {}).get('sha'):
            raise AdapterError('PR source or target changed while querying checks')
        selected = {name: checks.get(name, {'status': 'missing', 'sha': expected_sha}) for name in required_names}
        return {'status': 'pass' if all(c['status'] == 'pass' for c in selected.values()) else 'blocked',
                'checked_sha': expected_sha, 'checks': selected}

    def reconcile(self, number, evidence, current_target_sha, delivered_tree=None, delivered_reachable=False):
        pr = self.read_pr(number)
        head, base = pr.get('head', {}).get('sha'), pr.get('base', {}).get('sha')
        refs = {'source_sha': head, 'target_sha': current_target_sha, 'checked_sha': evidence.get('checked_sha'),
                'delivered_sha': pr.get('merge_commit_sha') if pr.get('merged') else None}
        def result(status, reason, verified=False):
            return dict(refs, status=status, reason=reason, verified_delivery=verified, pr=pr['number'])
        if pr.get('merged'):
            policy = self.config.get('github', {}).get('merge_policy') or self.config.get('github', {}).get('baseline_policy')
            if policy in ('queue', 'merge_queue') and (evidence.get('event') != 'merge_group' or not evidence.get('merge_group_sha') or evidence.get('checked_sha') != evidence['merge_group_sha']):
                return result('blocked', 'Merged queue result lacks actual merge_group evidence')
            if not refs['delivered_sha']:
                return result('blocked', 'Merged PR lacks delivered commit')
            # Caller must resolve actual commit tree via Git; covers squash/rebase identities.
            if (evidence.get('status') != 'pass' or head != evidence.get('source_sha') or
                    not evidence.get('candidate_tree') or delivered_tree != evidence['candidate_tree'] or
                    not delivered_reachable):
                return result('blocked', 'Actual delivery not mapped to verified content')
            return result('delivered', 'Actual merged content matches verified candidate', True)
        if head != evidence.get('source_sha') or current_target_sha != evidence.get('target_sha') or base != current_target_sha:
            return result('stale', 'Source or target baseline changed')
        if pr.get('state') != 'open':
            return result('blocked', 'PR closed without delivery')
        if evidence.get('status') != 'pass' or not evidence.get('checked_sha'):
            return result('blocked', 'Verification incomplete')
        return result('verified', 'Awaiting authorized delivery; queue/auto-merge is not completion')

    def ensure_pr(self, head, base, title, body, authorized=False):
        existing = self.find_pr(head, base)
        if existing:
            return existing
        if not authorized:
            raise AdapterError('PR creation requires explicit authorization')
        try:
            self._command(['pr', 'create', '--repo', self.repo_arg, '--head', head, '--base', base,
                           '--title', title, '--body', body, '--draft'], False)
        except AdapterError as exc:
            # Timeout might have happened after the write. Never blindly retry.
            existing = self.find_pr(head, base)
            if existing:
                return existing
            raise AdapterError('PR creation outcome unresolved; reconcile before retry') from exc
        existing = self.find_pr(head, base)
        if not existing:
            raise AdapterError('Created PR not yet observable; reconcile before retry')
        return existing

    @staticmethod
    def _review_readiness(pr, number):
        if pr.get('number') != int(number) or pr.get('state') != 'open' or pr.get('merged') is not False:
            raise AdapterError('Review readiness requires this exact open, unmerged PR')
        if not isinstance(pr.get('draft'), bool):
            raise AdapterError('PR draft state is unknown')
        return 'draft' if pr['draft'] else 'ready'

    def ready_for_review(self, number, authorized=False):
        """Promote a draft once; only a fresh native read confirms readiness.

        Without authorization this is read-only, also used by reconcile-ready.
        A timeout is an unknown write outcome: requery, never retry the write.
        """
        before = self.read_pr(number)
        status = self._review_readiness(before, number)
        if status == 'ready' or not authorized:
            return {'status': status, 'pr': int(number), 'observed': before}
        failure = None
        try:
            self._command(['pr', 'ready', str(int(number)), '--repo', self.repo_arg], False)
        except AdapterError as exc:
            failure = str(exc)
        try:
            after = self.read_pr(number)
            if self._review_readiness(after, number) == 'ready':
                return {'status': 'ready', 'pr': int(number), 'observed': after}
        except AdapterError as exc:
            return {'status': 'unknown', 'pr': int(number), 'reason': str(exc),
                    'operation': 'ready_for_review'}
        return {'status': 'unknown', 'pr': int(number), 'observed': after,
                'reason': failure or 'Draft-to-ready transition is not yet observable',
                'operation': 'ready_for_review'}

    def inspect_rules(self, branch, mechanism='rulesets'):
        """Read actual enforced baseline rules; never treat inaccessible as absent."""
        required, strict, queue = set(), False, False
        if mechanism == 'rulesets':
            rows = self._api(f'repos/{self.repository}/rules/branches/{quote(branch, safe="")}?per_page=100', True)
            for rule in rows:
                params = rule.get('parameters', {})
                if rule.get('type') == 'required_status_checks':
                    required.update(c['context'] for c in params.get('required_status_checks', []))
                    strict = strict or params.get('strict_required_status_checks_policy') is True
                queue = queue or rule.get('type') == 'merge_queue'
        elif mechanism == 'branch_protection':
            data = self._api(f'repos/{self.repository}/branches/{quote(branch, safe="")}/protection/required_status_checks')
            required.update(data.get('contexts', []))
            required.update(c['context'] for c in data.get('checks', []))
            strict = data.get('strict') is True
        else:
            raise AdapterError('Unknown server-rule mechanism')
        return {'policy': 'queue' if queue else ('strict' if strict and required else 'unsupported'),
                'required_checks': sorted(required), 'branch': branch, 'mechanism': mechanism,
                'rules_verified': bool(required and (strict or queue))}

    def request_merge(self, number, evidence, current_target_sha, authorized=False):
        if self._review_readiness(self.read_pr(number), number) != 'ready':
            raise AdapterError('Draft PR must be explicitly made ready before merge')
        state = self.reconcile(number, evidence, current_target_sha)
        if state['status'] != 'verified' or not authorized:
            raise AdapterError('Merge requires current verified evidence and explicit authorization')
        policy = self.config.get('github', {}).get('merge_policy') or self.config.get('github', {}).get('baseline_policy')
        if policy == 'strict_checks':
            policy = 'strict'
        if policy == 'merge_queue':
            policy = 'queue'
        if policy not in ('strict', 'queue'):
            raise AdapterError('Server strict/queue rules must be independently verified')
        # Enqueue may precede merge_group creation. Completion independently requires
        # merge_group evidence in reconcile; enqueue is only delivery_pending.
        if not evidence.get('baseline_verified'):
            raise AdapterError('Validated source/target combination evidence required')
        pr = self.read_pr(number)
        if evidence['checked_sha'] not in (pr['head']['sha'], pr.get('merge_commit_sha')):
            raise AdapterError('Pre-merge checks must name current head or GitHub test-merge commit')
        rules = self.inspect_rules(pr['base']['ref'], self.config['github'].get('rules_mechanism', 'rulesets'))
        if not rules['rules_verified'] or rules['policy'] != policy:
            raise AdapterError('Actual server rules no longer enforce configured baseline policy')
        required = sorted(set(rules['required_checks']) | set(self.config['github'].get('required_checks', [])))
        checks = self.checks(number, evidence['checked_sha'], required)
        if checks['status'] != 'pass':
            raise AdapterError('Required checks incomplete')
        if self.reconcile(number, evidence, current_target_sha)['status'] != 'verified':
            raise AdapterError('PR changed before merge request')
        if self._review_readiness(self.read_pr(number), number) != 'ready':
            raise AdapterError('PR returned to draft before merge request')
        # --match-head-commit plus server strict/queue rules close the source/base race.
        try:
            args = ['pr', 'merge', str(number), '--repo', self.repo_arg, '--auto',
                    '--match-head-commit', evidence['source_sha']]
            if policy == 'strict':
                args.append('--squash')
            self._command(args, False)
        except AdapterError as exc:
            observed = self.read_pr(number)
            # Read-only observation records a possible side effect, never retries it.
            return {'status': 'delivery_unknown', 'pr': number, 'observed': observed,
                    'reason': str(exc), 'remote_operation': 'merge_request_outcome_unknown'}
        return {'status': 'delivery_pending', 'pr': number, 'remote_operation': 'auto_merge_requested'}

    def commit_tree(self, sha):
        data = self._api(f'repos/{self.repository}/git/commits/{quote(sha, safe="")}')
        if data.get('sha') != sha or not data.get('tree', {}).get('sha'):
            raise AdapterError('GitHub commit/tree identity not verified')
        return data['tree']['sha']

    def merge_group_evidence(self, sha, number, required_names=None):
        """Only accept native run association; branch-name guesses are not proof."""
        pr = self.read_pr(number)
        pages = self._command(['api', '--hostname', self.hostname,
            f'repos/{self.repository}/actions/runs?head_sha={quote(sha, safe="")}&event=merge_group&per_page=100',
            '--paginate', '--slurp'])
        if not isinstance(pages, list) or not all(isinstance(p, dict) and isinstance(p.get('workflow_runs'), list) for p in pages):
            raise AdapterError('Malformed merge_group workflow response')
        runs = [r for p in pages for r in p['workflow_runs']]
        associated = []
        for run in runs:
            if run.get('head_sha') != sha or run.get('event') != 'merge_group':
                continue
            matches = [p for p in run.get('pull_requests', []) if p.get('number') == int(number)
                       and p.get('head', {}).get('sha') == pr['head']['sha']
                       and p.get('base', {}).get('ref') == pr['base']['ref']]
            if matches:
                associated.append(run)
        if not associated:
            raise AdapterError('No native merge_group association to this PR/head/base; queue completion remains blocked')
        latest = {}
        for run in associated:
            key = run.get('workflow_id')
            if key not in latest or (run.get('run_number', 0), run.get('run_attempt', 0)) > (latest[key].get('run_number', 0), latest[key].get('run_attempt', 0)):
                latest[key] = run
        if any(r.get('status') != 'completed' or r.get('conclusion') != 'success' for r in latest.values()):
            raise AdapterError('Associated merge_group workflow not successful')
        checks = self.checks(number, sha, required_names or self.config.get('github', {}).get('required_checks', []))
        if checks['status'] != 'pass':
            raise AdapterError('Required merge_group checks incomplete')
        return dict(checks, event='merge_group', merge_group_sha=sha, source_sha=pr['head']['sha'],
                    base_ref=pr['base']['ref'], runs=[{'id': r['id'], 'url': r.get('html_url')} for r in latest.values()])

    def _graphql(self, query, **variables):
        args = ['api', 'graphql', '--hostname', self.hostname, '-f', f'query={query}']
        for key, value in variables.items():
            args += ['-F' if isinstance(value, int) else '-f', f'{key}={value}']
        data = self._command(args)
        if not isinstance(data, dict) or data.get('errors') or not isinstance(data.get('data'), dict):
            raise AdapterError('GraphQL query/operation failed or returned incomplete data')
        return data['data']

    def remote_state(self, number):
        owner, repo = self.repository.split('/')
        data = self._graphql('query($owner:String!,$repo:String!,$number:Int!){repository(owner:$owner,name:$repo){pullRequest(number:$number){id state merged autoMergeRequest{enabledAt} mergeQueueEntry{id}}}}', owner=owner, repo=repo, number=int(number))
        pr = (data.get('repository') or {}).get('pullRequest')
        if not isinstance(pr, dict) or not pr.get('id') or not all(k in pr for k in ('merged', 'autoMergeRequest', 'mergeQueueEntry')):
            raise AdapterError('Remote merge state unavailable; cannot confirm cancellation')
        return pr

    def cancel_remote(self, number, authorized=False):
        before = self.remote_state(number)
        if before['merged']:
            return {'status': 'already_delivered', 'pr': number, 'observed': before,
                    'reason': 'Cancellation cannot undo an already merged PR'}
        if before['autoMergeRequest'] is None and before['mergeQueueEntry'] is None:
            return {'status': 'cancelled', 'pr': number, 'observed': before}
        if not authorized:
            raise AdapterError('Remote cancellation requires explicit authorization')
        try:
            if before['autoMergeRequest'] is not None:
                self._graphql('mutation($id:ID!){disablePullRequestAutoMerge(input:{pullRequestId:$id}){pullRequest{id}}}', id=before['id'])
            # Requery between effects: disabling auto-merge can also dequeue.
            interim = self.remote_state(number)
            if not interim['merged'] and interim['mergeQueueEntry'] is not None:
                self._graphql('mutation($id:ID!){dequeuePullRequest(input:{id:$id}){mergeQueueEntry{id}}}', id=interim['id'])
        except AdapterError as exc:
            try:
                after = self.remote_state(number)
            except AdapterError:
                return {'status': 'unknown', 'pr': number, 'reason': str(exc)}
        else:
            after = self.remote_state(number)
        if after['merged']:
            return {'status': 'already_delivered', 'pr': number, 'observed': after}
        if after['autoMergeRequest'] is None and after['mergeQueueEntry'] is None:
            return {'status': 'cancelled', 'pr': number, 'observed': after}
        return {'status': 'unknown', 'pr': number, 'observed': after, 'reason': 'Remote operation still active; local waiting stopped only'}

    def wait_checks(self, number, expected_sha, required_names, budget, persist, *, queue=False,
                    cancelled=lambda: False, sleep=time.sleep, now=time.time):
        """Persistent total budget; reserve query attempt before any API call.

        persist(snapshot) must atomically save within the owning Controller lock.
        Wall-clock start survives restart (including downtime); caller must retain
        this budget for this operation instead of passing a fresh dictionary.
        """
        if not callable(persist):
            raise AdapterError('Waiting requires durable budget persistence')
        limits = self.config.get('limits', {})
        maximum = limits.get('merge_queue_wait_seconds' if queue else 'ci_wait_seconds', 300)
        attempts = limits.get('query_attempts', 20)
        interval = limits.get('poll_seconds', 2)
        if (type(maximum) not in (int, float) or not math.isfinite(maximum) or maximum <= 0
                or type(attempts) is not int or attempts < 1
                or type(interval) not in (int, float) or not math.isfinite(interval) or interval <= 0):
            raise AdapterError('Invalid finite GitHub wait limits')
        identity = {'number': int(number), 'checked_sha': expected_sha, 'queue': bool(queue)}
        if budget.get('identity') not in (None, identity):
            raise AdapterError('Cannot reuse wait budget for different PR/check identity')
        budget.setdefault('identity', identity)
        budget.setdefault('started_at', now())
        budget.setdefault('attempts', 0)
        budget.setdefault('elapsed_seconds', 0)
        while True:
            elapsed = max(budget['elapsed_seconds'], now() - budget['started_at'])
            budget['elapsed_seconds'] = elapsed
            if cancelled():
                budget['status'] = 'cancelled_local'
                persist(dict(budget))
                return {'status': 'cancelled_local', 'budget': dict(budget), 'remote_cancelled': False}
            if budget['attempts'] >= attempts or elapsed >= maximum:
                budget['status'] = 'exhausted'
                persist(dict(budget))
                return {'status': 'blocked', 'reason': 'GitHub total wait/query budget exhausted', 'budget': dict(budget)}
            budget['attempts'] += 1
            budget['status'] = 'querying'
            persist(dict(budget))
            self._deadline = time.monotonic() + (maximum - elapsed)
            try:
                result = self.merge_group_evidence(expected_sha, number, required_names) if queue else self.checks(number, expected_sha, required_names)
            except AdapterError as exc:
                budget.update(status='blocked', elapsed_seconds=max(elapsed, now() - budget['started_at']), last_error=str(exc))
                persist(dict(budget))
                return {'status': 'blocked', 'reason': str(exc), 'budget': dict(budget)}
            finally:
                self._deadline = None
            budget['elapsed_seconds'] = max(elapsed, now() - budget['started_at'])
            if result.get('status') == 'pass':
                budget['status'] = 'pass'
                persist(dict(budget))
                return dict(result, budget=dict(budget))
            if any(c.get('status') not in ('pending', 'missing') for c in result.get('checks', {}).values() if c.get('status') != 'pass'):
                budget['status'] = 'failed'
                persist(dict(budget))
                return dict(result, budget=dict(budget))
            budget['status'] = 'waiting'
            persist(dict(budget))
            remaining = maximum - budget['elapsed_seconds']
            if remaining > 0:
                sleep(min(interval, remaining))

    def complete_issue(self, task_id, delivery, body, authorized=False):
        """Publish idempotent delivery receipt and close only verified delivered task.

        The Controller supplies its tamper-checked delivery record, not user JSON.
        Unknown writes are reconciled once, never automatically repeated.
        """
        repo, number = self._identity(task_id)
        if repo != self.repository:
            raise AdapterError('Cannot complete a task in a different repository')
        if (delivery.get('status') != 'delivered' or delivery.get('verified_delivery') is not True
                or not delivery.get('delivered_sha') or not delivery.get('pr')):
            raise AdapterError('Issue completion requires verified actual delivery record')
        pr = self.read_pr(delivery['pr'])
        sha = delivery['delivered_sha']
        if not pr.get('merged') or pr.get('merge_commit_sha') != sha or pr['head']['sha'] != delivery.get('source_sha'):
            raise AdapterError('Delivery record does not match actual merged PR')
        target = self._api(f'repos/{repo}/git/ref/heads/{quote(pr["base"]["ref"], safe="")}')
        tip = target.get('object', {}).get('sha')
        if not tip:
            raise AdapterError('Cannot resolve actual target branch')
        comparison = self._api(f'repos/{repo}/compare/{quote(sha, safe="")}...{quote(tip, safe="")}')
        if comparison.get('status') not in ('ahead', 'identical') or comparison.get('base_commit', {}).get('sha') != sha:
            raise AdapterError('Delivered commit is not verified on actual target branch')
        task = self.read_task(task_id)
        marker = f'<!-- harness-delivery:{hashlib.sha256((task["id"] + ":" + sha).encode()).hexdigest()} -->'
        receipt_body = f'{marker}\nVerified delivery: {sha}\nPR: #{pr["number"]}\n\n{body}'
        endpoint = f'repos/{repo}/issues/{number}/comments'
        def receipts():
            return [c for c in self._api(endpoint + '?per_page=100', True) if marker in (c.get('body') or '')]
        existing = receipts()
        if len(existing) > 1:
            raise AdapterError('Duplicate delivery receipts require reconciliation')
        if not authorized and (not existing or task['state'] != 'closed' or task.get('state_reason') != 'completed'):
            raise AdapterError('Issue result publication/closure requires explicit authorization')
        if not existing:
            try:
                self._command(['api', '--hostname', self.hostname, '--method', 'POST', endpoint, '-f', f'body={receipt_body}'])
            except AdapterError as exc:
                existing = receipts()
                if not existing:
                    return {'status': 'unknown', 'task_id': task['id'], 'reason': str(exc), 'operation': 'issue_receipt'}
            else:
                existing = receipts()
                if len(existing) != 1:
                    return {'status': 'unknown', 'task_id': task['id'], 'reason': 'Receipt write not observable', 'operation': 'issue_receipt'}
        if len(existing) != 1 or existing[0].get('body') != receipt_body:
            raise AdapterError('Delivery receipt conflict; do not overwrite or duplicate external content')
        # A closed issue without this verified delivery receipt is never completion.
        if task['state'] != 'closed' or task.get('state_reason') != 'completed':
            try:
                self._command(['api', '--hostname', self.hostname, '--method', 'PATCH', f'repos/{repo}/issues/{number}',
                               '-f', 'state=closed', '-f', 'state_reason=completed'])
            except AdapterError:
                pass  # Reconcile once; never repeat an uncertain close operation here.
        observed = self.read_task(task_id)
        if observed['state'] != 'closed' or observed.get('state_reason') != 'completed':
            return {'status': 'unknown', 'task_id': task['id'], 'operation': 'issue_close', 'observed': observed}
        return {'status': 'completed', 'task_id': task['id'], 'delivered_sha': sha, 'pr': pr['number'],
                'receipt_url': existing[0].get('html_url'), 'receipt_id': existing[0].get('id'), 'issue': observed}



def core_id(source_id):
    """Report-safe identity; full digest includes host, repository, and issue."""
    return 'gh-' + hashlib.sha256(source_id.encode('utf-8')).hexdigest()


def normalize_graph(graph):
    tasks, dependencies = {}, {}
    for source_id, task in graph['tasks'].items():
        key = core_id(source_id)
        if key in tasks and tasks[key]['source_id'] != source_id:
            raise AdapterError('Core task identity collision')
        tasks[key] = dict(task, id=key, source_id=source_id)
        dependencies[key] = [core_id(x) for x in graph['dependencies'][source_id]]
        tasks[key]['dependencies'] = dependencies[key]
    return {'tasks': tasks, 'dependencies': dependencies}


def github_action(config, action, args, run=None, persist=None, cancelled=lambda: False):
    """CLI bridge. Caller persists returned evidence/checkpoint under its run lock.

    args is a dict (or argparse Namespace). Read actions: tasks, graph, read,
    dependencies, find-pr, checks, reconcile, rules. Mutation actions create-pr,
    merge additionally require args.authorized exactly True. Never infers mode.
    """
    if config.get('mode') != 'github':
        raise AdapterError('GitHub action requires explicit github mode')
    args = args if isinstance(args, dict) else vars(args)
    adapter = GitHubAdapter(config, run)
    if action == 'tasks':
        return [dict(t, id=core_id(t['id']), source_id=t['id']) for t in adapter.list_tasks()]
    if action == 'graph': return normalize_graph(adapter.dependency_graph())
    if action == 'read': return adapter.read_task(args['task_id'])
    if action == 'dependencies': return adapter.dependencies(args['task_id'])
    if action == 'find-pr': return adapter.find_pr(args['head'], args['base'])
    if action == 'checks':
        return adapter.checks(args['number'], args['expected_sha'], args.get('required_names', config.get('github', {}).get('required_checks', [])))
    if action == 'rules': return adapter.inspect_rules(args['base'], args.get('mechanism', 'rulesets'))
    if action == 'reconcile':
        return adapter.reconcile(args['number'], args['evidence'], args['current_target_sha'],
                                 args.get('delivered_tree'), args.get('delivered_reachable') is True)
    if action == 'commit-tree': return adapter.commit_tree(args['sha'])
    if action == 'merge-group': return adapter.merge_group_evidence(args['sha'], args['number'], args.get('required_names'))
    if action == 'remote-state': return adapter.remote_state(args['number'])
    if action == 'cancel': return adapter.cancel_remote(args['number'], args.get('authorized') is True)
    if action == 'wait-checks':
        return adapter.wait_checks(args['number'], args['expected_sha'], args.get('required_names', config.get('github', {}).get('required_checks', [])),
                                   args['budget'], persist, queue=args.get('queue', False), cancelled=cancelled)
    if action == 'complete-issue':
        return adapter.complete_issue(args['task_id'], args['delivery'], args.get('body', ''), args.get('authorized') is True)
    if action == 'ready': return adapter.ready_for_review(args['number'], args.get('authorized') is True)
    if action == 'reconcile-ready': return adapter.ready_for_review(args['number'], False)
    if action == 'create-pr':
        return adapter.ensure_pr(args['head'], args['base'], args['title'], args['body'], args.get('authorized') is True)
    if action == 'merge':
        return adapter.request_merge(args['number'], args['evidence'], args['current_target_sha'], args.get('authorized') is True)
    raise AdapterError(f'Unknown GitHub action: {action}')
