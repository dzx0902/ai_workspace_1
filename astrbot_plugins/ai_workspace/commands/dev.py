from __future__ import annotations

from astrbot.api.event import AstrMessageEvent, filter

from ..utils import command_args, text_result


class DevCommands:
    @filter.command("repos")
    async def repos(self, event: AstrMessageEvent):
        data = self.workspace_client.get("/dev/repos")
        repos = data.get("repos", [])
        if not repos:
            yield event.plain_result("No allowed repos found.")
            return
        yield event.plain_result("\n".join(repo["name"] for repo in repos))

    @filter.command("dev")
    async def dev(self, event: AstrMessageEvent):
        args = command_args(event.message_str, "dev")
        if len(args) < 2:
            yield event.plain_result("Usage: /dev <plan|patch|review|test|diff|apply|task> <repo_name|task_id> ...")
            return
        action, repo_name = args[0], args[1]
        if action == "plan":
            data = self.workspace_client.post("/dev/plan", {"repo_name": repo_name, "task_description": " ".join(args[2:])})
        elif action == "patch":
            data = self.workspace_client.post("/dev/patch", {"repo_name": repo_name, "task_description": " ".join(args[2:])})
        elif action == "review":
            data = self.workspace_client.post("/dev/review", {"repo_name": repo_name, "task_description": " ".join(args[2:])})
        elif action == "test":
            data = self.workspace_client.post("/dev/test", {"repo_name": repo_name, "command": " ".join(args[2:]), "allow_shell": True})
        elif action == "diff":
            data = self.workspace_client.post("/dev/diff", {"repo_name": repo_name})
        elif action == "apply":
            data = self.workspace_client.post("/dev/apply", {"task_id": repo_name, "confirm": True})
        elif action == "task" and len(args) >= 4:
            data = self.workspace_client.post(
                "/dev/task",
                {"repo_name": repo_name, "task_type": args[2], "task_description": " ".join(args[3:])},
            )
        else:
            yield event.plain_result("Unsupported /dev action.")
            return
        yield event.plain_result(text_result(data))
