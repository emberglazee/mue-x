"""Swarm Orchestrator — Multi-agent collaboration framework.

Mue can spawn specialized sub-agents that work concurrently on independent
tasks. Each agent has a role (searcher, analyzer, coder, reviewer, miner).
Agents communicate via a shared message bus and report results back to the
orchestrator, which aggregates and feeds insights into the main evolution loop.

This is how Mue scales: instead of doing everything sequentially in one
agent, it delegates to a swarm of focused workers.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from queue import Queue


AGENT_ROLES = ["searcher", "analyzer", "coder", "reviewer", "miner"]


@dataclass
class SwarmMessage:
    """A message between swarm agents."""
    msg_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    sender: str = ""
    recipient: str = ""  # "" = broadcast
    msg_type: str = "info"  # info, task, result, alert
    content: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class SwarmTask:
    """A task delegated to a swarm agent."""
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    role: str = "analyzer"
    description: str = ""
    context: dict = field(default_factory=dict)
    status: str = "pending"  # pending, assigned, running, done, failed
    assigned_to: str = ""
    result: dict | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float = 0.0


class SwarmAgent:
    """A lightweight specialized agent in the swarm.

    Each agent has a role and processes tasks matching that role.
    Agents don't evolve independently — they feed results back to
    the orchestrator which drives the main evolution loop.
    """

    def __init__(self, name: str, role: str, orchestrator: "SwarmOrchestrator"):
        self.name = name
        self.role = role
        self.orchestrator = orchestrator
        self.agent_id = uuid.uuid4().hex[:8]
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.active = True

    def process(self, task: SwarmTask) -> dict:
        """Process a delegated task. Returns result dict."""
        handlers = {
            "searcher": self._search,
            "analyzer": self._analyze,
            "coder": self._code,
            "reviewer": self._review,
            "miner": self._mine,
        }
        handler = handlers.get(self.role, self._analyze)
        try:
            result = handler(task)
            self.tasks_completed += 1
            return result
        except Exception as e:
            self.tasks_failed += 1
            return {"error": str(e), "role": self.role}

    def _search(self, task: SwarmTask) -> dict:
        """Real search: use orchestrator's tools or scan local filesystem."""
        results = []
        query = task.description

        # If orchestrator has memory, search it
        if self.orchestrator.memory:
            try:
                memories = self.orchestrator.memory.search_fts(query, limit=5)
                results.extend([m.content[:120] for m in memories])
            except Exception:
                pass

        # If orchestrator has genome, search genes
        if self.orchestrator.genome:
            for name, gene in self.orchestrator.genome.genes.items():
                if any(kw in name.lower() for kw in query.lower().split()[:3]):
                    results.append(f"Gene match: {name} (fitness={gene.fitness:.2f})")

        return {
            "role": "searcher",
            "task": task.description[:100],
            "findings": results or [f"No results for: {query[:80]}"],
            "sources": task.context.get("sources", []),
        }

    def _analyze(self, task: SwarmTask) -> dict:
        """Real analysis: examine genes for patterns, issues, and opportunities."""
        insights = []
        if self.orchestrator.genome:
            for name, gene in self.orchestrator.genome.genes.items():
                if name in ("mutator", "genome", "inspector", "solidify"):
                    continue
                # Analyze fitness trends
                if gene.fitness < 0.3 and gene.mutation_count > 2:
                    insights.append(f"Weak gene: {name} (fitness={gene.fitness:.2f}, {gene.mutation_count} mutations)")
                elif gene.fitness > 0.7:
                    insights.append(f"Strong gene: {name} (fitness={gene.fitness:.2f})")
                # Check for recent mutation activity
                if gene.last_mutated:
                    insights.append(f"Recently mutated: {name} at {gene.last_mutated[:16]}")

        if not insights:
            insights.append(f"No actionable insights from analysis of {len(self.orchestrator.genome.genes) if self.orchestrator.genome else 0} genes")

        return {
            "role": "analyzer",
            "task": task.description[:100],
            "analysis": f"Analyzed {len(self.orchestrator.genome.genes) if self.orchestrator.genome else 0} genes",
            "insights": insights[:10],
        }

    def _code(self, task: SwarmTask) -> dict:
        """Code generation: produce a mutation by pattern-matching from atouts/memory."""
        code_generated = False
        snippet = ""
        if self.orchestrator.memory:
            try:
                memories = self.orchestrator.memory.search_fts(
                    f"pattern code {task.description}", limit=3
                )
                for m in memories:
                    if "def " in m.content or "class " in m.content:
                        snippet = m.content[:500]
                        code_generated = True
                        break
            except Exception:
                pass
        return {
            "role": "coder",
            "task": task.description[:100],
            "code_generated": code_generated,
            "snippet": snippet[:200] if snippet else "",
            "language": task.context.get("language", "python"),
        }

    def _review(self, task: SwarmTask) -> dict:
        """Real review: AST-parse gene sources, count issues."""
        import ast
        issues_found = 0
        suggestions = []
        if self.orchestrator.genome:
            for name, gene in self.orchestrator.genome.genes.items():
                if name in ("mutator", "genome", "inspector", "solidify"):
                    continue
                try:
                    source = gene.source_path.read_text(encoding="utf-8")
                    tree = ast.parse(source)
                    # Count potential issues
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Try):
                            if not node.handlers:
                                issues_found += 1
                                suggestions.append(f"Gene '{name}': bare try without except")
                    if len(source.split("\n")) > 300:
                        issues_found += 1
                        suggestions.append(f"Gene '{name}': file too long ({len(source.split(chr(10)))} lines)")
                except Exception:
                    issues_found += 1
                    suggestions.append(f"Gene '{name}': unparseable")
        quality = max(0.1, 1.0 - issues_found * 0.1)
        return {
            "role": "reviewer",
            "task": task.description[:100],
            "issues_found": issues_found,
            "suggestions": suggestions[:5],
            "quality_score": round(quality, 2),
        }

    def _mine(self, task: SwarmTask) -> dict:
        """Real mining: trigger absorption from orchestrator's miner if available."""
        patterns_found = 0
        if self.orchestrator.miner:
            try:
                absorbed = self.orchestrator.miner.auto_mine_tick(
                    cycle_count=self.tasks_completed,
                    domain=task.context.get("domain", "general"),
                )
                patterns_found = len(absorbed)
            except Exception:
                pass
        return {
            "role": "miner",
            "task": task.description[:100],
            "patterns_found": patterns_found,
            "repos_scanned": task.context.get("repos", []),
        }

    @property
    def stats(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "active": self.active,
        }


class SwarmOrchestrator:
    """Coordinates a swarm of specialized Mue sub-agents.

    The orchestrator:
    1. Receives complex tasks that benefit from parallelization
    2. Decomposes them into sub-tasks for different roles
    3. Assigns to available agents
    4. Aggregates results
    5. Feeds insights back to the main agent's evolution loop

    This enables Mue to:
    - Search + Analyze + Code simultaneously
    - Review its own code changes from an independent perspective
    - Mine GitHub while continuing other work
    - Scale to handle complex multi-step operations
    """

    def __init__(self, agent_name: str = "Mue", max_agents: int = 10):
        self.agent_name = agent_name
        self.max_agents = max_agents
        self.agents: dict[str, SwarmAgent] = {}
        self.message_bus: Queue = Queue()
        self.task_queue: list[SwarmTask] = []
        self.completed_tasks: list[SwarmTask] = []
        self._lock = threading.Lock()
        # Resources for agent handlers — set by MueAgent after creation
        self.memory = None
        self.genome = None
        self.miner = None

        # Spawn default agents
        for role in AGENT_ROLES:
            self.spawn_agent(role=f"{role}-alpha", role_type=role)

    def spawn_agent(self, role: str, role_type: str = "analyzer") -> str:
        """Create a new swarm agent with the given role."""
        if len(self.agents) >= self.max_agents:
            return ""
        agent = SwarmAgent(name=role, role=role_type, orchestrator=self)
        with self._lock:
            self.agents[agent.agent_id] = agent
        self.broadcast(SwarmMessage(
            sender="orchestrator",
            msg_type="info",
            content=f"Agent {role} ({agent.agent_id}) joined the swarm",
        ))
        return agent.agent_id

    def remove_agent(self, agent_id: str):
        """Remove an agent from the swarm."""
        with self._lock:
            if agent_id in self.agents:
                self.agents[agent_id].active = False
                del self.agents[agent_id]

    def delegate(self, description: str, roles: list[str] = None,
                 context: dict = None) -> list[str]:
        """Delegate a task to agents with specific roles.

        Returns list of task IDs.
        """
        roles = roles or ["analyzer"]
        context = context or {}
        task_ids = []

        for role in roles:
            task = SwarmTask(role=role, description=description, context=context)
            with self._lock:
                self.task_queue.append(task)
            task_ids.append(task.task_id)

        return task_ids

    def tick(self) -> dict:
        """Process one orchestration cycle.

        Assigns pending tasks to available agents, collects results.
        Returns summary of swarm activity.
        """
        results = {
            "tasks_assigned": 0,
            "tasks_completed": 0,
            "results_collected": 0,
            "agents_active": 0,
        }

        # Assign pending tasks to matching agents
        with self._lock:
            available = [a for a in self.agents.values() if a.active]
            results["agents_active"] = len(available)

            remaining = []
            for task in self.task_queue:
                if task.status != "pending":
                    remaining.append(task)
                    continue

                # Find matching agent
                matching = [a for a in available if a.role == task.role]
                if matching:
                    agent = matching[0]
                    task.status = "running"
                    task.assigned_to = agent.agent_id
                    results["tasks_assigned"] += 1

                    # Process synchronously for now (thread pool later)
                    task.result = agent.process(task)
                    task.status = "done"
                    task.completed_at = time.time()
                    results["tasks_completed"] += 1

                    # Aggregate into completed
                    self.completed_tasks.append(task)
                    if len(self.completed_tasks) > 500:
                        self.completed_tasks = self.completed_tasks[-500:]

                    results["results_collected"] += 1
                else:
                    remaining.append(task)

            self.task_queue = remaining

        return results

    def broadcast(self, message: SwarmMessage):
        """Send a message to all agents via the message bus."""
        self.message_bus.put(message)

    def get_insights(self, limit: int = 5) -> list[dict]:
        """Extract insights from recently completed tasks.

        These insights feed back into the main evolution loop,
        providing real data for mutation decisions.
        """
        insights = []
        with self._lock:
            recent = sorted(self.completed_tasks,
                          key=lambda t: t.completed_at, reverse=True)[:limit]
            for task in recent:
                if task.result and "error" not in task.result:
                    insights.append({
                        "task_id": task.task_id,
                        "role": task.role,
                        "description": task.description[:200],
                        "result_summary": str(task.result)[:200],
                    })
        return insights

    def shutdown(self):
        """Gracefully shut down all agents."""
        for agent in list(self.agents.values()):
            agent.active = False
        with self._lock:
            self.agents.clear()
        self.broadcast(SwarmMessage(
            sender="orchestrator",
            msg_type="alert",
            content="Swarm shutting down",
        ))

    @property
    def stats(self) -> dict:
        with self._lock:
            return {
                "total_agents": len(self.agents),
                "active_agents": sum(1 for a in self.agents.values() if a.active),
                "pending_tasks": sum(1 for t in self.task_queue if t.status == "pending"),
                "running_tasks": sum(1 for t in self.task_queue if t.status == "running"),
                "completed_tasks": len(self.completed_tasks),
                "agent_details": [a.stats for a in self.agents.values()],
            }
